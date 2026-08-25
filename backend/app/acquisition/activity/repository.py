"""Internal query repository for Acquisition Activity Timeline.

Append-only: this module intentionally exposes **no** update/delete methods.

**Canonical list order (the only allowed order):**
``occurred_at ASC``, then ``id ASC``.

Never order by ``recorded_at``. HTTP/UI layers must not invent alternate sorts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final, Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent

# Sole legal sort for Activity Timeline lists / cursors.
ACTIVITY_LIST_ORDER: Final[tuple[str, str]] = ("occurred_at", "id")


def _stable_order(stmt: Select[tuple[AcquisitionActivityEvent]]) -> Select[
    tuple[AcquisitionActivityEvent]
]:
    # Locked: occurred_at, id — do not add recorded_at or caller-selected ORDER BY.
    return stmt.order_by(
        AcquisitionActivityEvent.occurred_at.asc(),
        AcquisitionActivityEvent.id.asc(),
    )


async def get_activity_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    event_id: str,
) -> AcquisitionActivityEvent | None:
    """Internal helper (not part of the Stage 3E public write/read surface)."""
    stmt = select(AcquisitionActivityEvent).where(
        AcquisitionActivityEvent.tenant_id == tenant_id,
        AcquisitionActivityEvent.id == event_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_source_event_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_event_id: str,
) -> AcquisitionActivityEvent | None:
    """Internal idempotency lookup (used by append; not a public API)."""
    stmt = select(AcquisitionActivityEvent).where(
        AcquisitionActivityEvent.tenant_id == tenant_id,
        AcquisitionActivityEvent.source_event_id == source_event_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_activity_events(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str | None = None,
    flight_id: str | None = None,
    endpoint_id: str | None = None,
    submission_id: str | None = None,
    result_id: str | None = None,
    outcome_id: str | None = None,
    event_types: Sequence[str] | None = None,
    occurred_after: datetime | None = None,
    occurred_before: datetime | None = None,
    after_occurred_at: datetime | None = None,
    after_id: str | None = None,
    limit: int = 100,
) -> list[AcquisitionActivityEvent]:
    """List events for a tenant with optional Acquisition-context filters.

    Order is fixed to :data:`ACTIVITY_LIST_ORDER` (``occurred_at``, ``id``).
    Cursor: pass the last row's ``occurred_at`` + ``id`` as ``after_*``.
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if limit > 500:
        raise ValueError("limit must be <= 500")

    stmt = select(AcquisitionActivityEvent).where(
        AcquisitionActivityEvent.tenant_id == tenant_id,
    )
    if campaign_id is not None:
        stmt = stmt.where(AcquisitionActivityEvent.campaign_id == campaign_id)
    if flight_id is not None:
        stmt = stmt.where(AcquisitionActivityEvent.flight_id == flight_id)
    if endpoint_id is not None:
        stmt = stmt.where(AcquisitionActivityEvent.endpoint_id == endpoint_id)
    if submission_id is not None:
        stmt = stmt.where(AcquisitionActivityEvent.submission_id == submission_id)
    if result_id is not None:
        stmt = stmt.where(AcquisitionActivityEvent.result_id == result_id)
    if outcome_id is not None:
        stmt = stmt.where(AcquisitionActivityEvent.outcome_id == outcome_id)
    if event_types:
        stmt = stmt.where(AcquisitionActivityEvent.event_type.in_(list(event_types)))
    if occurred_after is not None:
        stmt = stmt.where(AcquisitionActivityEvent.occurred_at > occurred_after)
    if occurred_before is not None:
        stmt = stmt.where(AcquisitionActivityEvent.occurred_at < occurred_before)
    if after_occurred_at is not None and after_id is not None:
        stmt = stmt.where(
            (AcquisitionActivityEvent.occurred_at > after_occurred_at)
            | (
                (AcquisitionActivityEvent.occurred_at == after_occurred_at)
                & (AcquisitionActivityEvent.id > after_id)
            )
        )
    elif after_occurred_at is not None or after_id is not None:
        raise ValueError("after_occurred_at and after_id must be provided together")

    stmt = _stable_order(stmt).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


__all__ = [
    "ACTIVITY_LIST_ORDER",
    "get_activity_event",
    "get_by_source_event_id",
    "list_activity_events",
]
