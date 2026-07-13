"""Outbox dispatcher — claim, deliver, retry, DLQ."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.platform.events.envelope import EventEnvelope
from backend.app.platform.events.outbox.model import DomainEventOutbox
from backend.app.platform.events.outbox.statuses import OutboxStatus
from backend.app.platform.events.registry import get_event_contract_registry

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 25
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_PROCESSING_TIMEOUT_SECONDS = 120
DEFAULT_BACKOFF_BASE_SECONDS = 2


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_envelope(row: DomainEventOutbox) -> EventEnvelope:
    return EventEnvelope(
        event_id=row.event_id,
        event_type=row.event_type,
        event_version=row.event_version,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        tenant_id=row.tenant_id,
        company_id=row.company_id,
        payload=dict(row.payload or {}),
        occurred_at=row.occurred_at,
        correlation_id=row.correlation_id,
        causation_id=row.causation_id,
    )


@dataclass(frozen=True)
class DispatchStats:
    claimed: int = 0
    processed: int = 0
    failed: int = 0
    dead_letter: int = 0
    requeued_stale: int = 0


async def requeue_stale_processing_rows(
    db: AsyncSession,
    *,
    worker_id: str,
    timeout_seconds: int = DEFAULT_PROCESSING_TIMEOUT_SECONDS,
    now: Optional[datetime] = None,
) -> int:
    """Reset rows stuck in processing longer than timeout."""
    ts = now or _utcnow()
    cutoff = ts - timedelta(seconds=max(1, timeout_seconds))
    result = await db.execute(
        update(DomainEventOutbox)
        .where(
            DomainEventOutbox.status == OutboxStatus.processing.value,
            DomainEventOutbox.locked_at.is_not(None),
            DomainEventOutbox.locked_at < cutoff,
        )
        .values(
            status=OutboxStatus.pending.value,
            locked_at=None,
            locked_by=None,
            last_error=f"processing timeout reclaimed by {worker_id}",
            available_at=ts,
        )
    )
    return int(result.rowcount or 0)


async def claim_outbox_batch(
    db: AsyncSession,
    *,
    worker_id: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    now: Optional[datetime] = None,
) -> list[DomainEventOutbox]:
    """Claim pending rows using row-level lock (SKIP LOCKED on Postgres)."""
    ts = now or _utcnow()
    bind = db.get_bind()
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "postgresql") if bind else "postgresql"
    stmt = (
        select(DomainEventOutbox)
        .where(
            DomainEventOutbox.status == OutboxStatus.pending.value,
            DomainEventOutbox.available_at <= ts,
        )
        .order_by(DomainEventOutbox.occurred_at.asc())
        .limit(max(1, batch_size))
    )
    if dialect_name == "sqlite":
        stmt = stmt.with_for_update()
    else:
        stmt = stmt.with_for_update(skip_locked=True)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    for row in rows:
        row.status = OutboxStatus.processing.value
        row.locked_at = ts
        row.locked_by = worker_id
        row.attempt_count = int(row.attempt_count or 0) + 1
    if rows:
        await db.flush()
    return rows


def _backoff_seconds(attempt_count: int, base: int = DEFAULT_BACKOFF_BASE_SECONDS) -> int:
    return min(base * (2 ** max(0, attempt_count - 1)), 3600)


async def mark_outbox_processed(
    db: AsyncSession,
    row: DomainEventOutbox,
    *,
    now: Optional[datetime] = None,
) -> None:
    """Mark outbox row consumed successfully (after consumer commit)."""
    ts = now or _utcnow()
    row.status = OutboxStatus.processed.value
    row.processed_at = ts
    row.last_error = None
    row.locked_at = None
    row.locked_by = None
    await db.flush()


async def mark_outbox_failed(
    db: AsyncSession,
    row: DomainEventOutbox,
    *,
    error: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    now: Optional[datetime] = None,
) -> OutboxStatus:
    ts = now or _utcnow()
    row.last_error = (error or "unknown error")[:4000]
    row.locked_at = None
    row.locked_by = None
    if int(row.attempt_count or 0) >= max(1, max_attempts):
        row.status = OutboxStatus.dead_letter.value
        row.processed_at = ts
        final = OutboxStatus.dead_letter
    else:
        row.status = OutboxStatus.pending.value
        row.available_at = ts + timedelta(seconds=_backoff_seconds(int(row.attempt_count or 1)))
        final = OutboxStatus.failed
    await db.flush()
    return final


async def dispatch_outbox_batch(
    db: AsyncSession,
    consumer,
    *,
    worker_id: str = "outbox-dispatcher",
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    processing_timeout_seconds: int = DEFAULT_PROCESSING_TIMEOUT_SECONDS,
) -> DispatchStats:
    """
    Claim a batch, invoke consumer, update row status.

    Transaction boundaries (at-least-once):
    1. Claim rows → commit (short TX; lock released before consumer runs).
    2. Consumer + receipt + outbox `processed` → single commit.
    3. Consumer failure → rollback (no receipt) → retry/DLQ in fresh TX.

    Long-running consumer work must stay outside the claim transaction. Current
    skeleton is log-only; business actions in 3A-4+ must respect the same boundary.
    """
    requeued = await requeue_stale_processing_rows(
        db,
        worker_id=worker_id,
        timeout_seconds=processing_timeout_seconds,
    )
    rows = await claim_outbox_batch(db, worker_id=worker_id, batch_size=batch_size)
    stats = DispatchStats(claimed=len(rows), requeued_stale=requeued)
    if not rows:
        return stats

    envelopes = [_to_envelope(row) for row in rows]
    event_ids = [row.event_id for row in rows]
    await db.commit()

    processed = failed = dead = 0
    registry = get_event_contract_registry()

    for event_id, envelope in zip(event_ids, envelopes):
        row = await db.get(DomainEventOutbox, event_id)
        if row is None:
            continue
        try:
            registry.validate_envelope(
                event_type=envelope.event_type,
                event_version=envelope.event_version,
                payload=envelope.payload,
            )
            await consumer.handle(envelope)
            await mark_outbox_processed(db, row)
            await db.commit()
            processed += 1
            logger.info(
                "domain_event.outbox.processed event_id=%s type=%s correlation=%s",
                envelope.event_id,
                envelope.event_type,
                envelope.correlation_id,
            )
        except Exception as exc:
            await db.rollback()
            row = await db.get(DomainEventOutbox, event_id)
            if row is None:
                continue
            final = await mark_outbox_failed(db, row, error=str(exc), max_attempts=max_attempts)
            await db.commit()
            if final == OutboxStatus.dead_letter:
                dead += 1
            else:
                failed += 1
            logger.exception(
                "domain_event.outbox.failed event_id=%s type=%s attempt=%s",
                envelope.event_id,
                envelope.event_type,
                row.attempt_count,
            )

    return DispatchStats(
        claimed=stats.claimed,
        processed=processed,
        failed=failed,
        dead_letter=dead,
        requeued_stale=requeued,
    )
