"""Publish domain events into transactional outbox."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.platform.events.envelope import EventEnvelope
from backend.app.platform.events.outbox.model import DomainEventOutbox
from backend.app.platform.events.registry import get_event_contract_registry

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_envelope(
    *,
    event_type: str,
    event_version: str,
    aggregate_type: str,
    aggregate_id: str,
    tenant_id: str,
    payload: dict[str, Any],
    occurred_at: Optional[datetime] = None,
    company_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> EventEnvelope:
    registry = get_event_contract_registry()
    registry.validate_envelope(
        event_type=event_type,
        event_version=event_version,
        payload=payload,
    )
    when = occurred_at or _utcnow()
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return EventEnvelope.new(
        event_type=event_type,
        event_version=event_version,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        tenant_id=tenant_id,
        company_id=company_id,
        payload=payload,
        occurred_at=when,
        correlation_id=correlation_id,
        causation_id=causation_id,
        event_id=event_id,
    )


async def publish_domain_event(
    db: AsyncSession,
    envelope: EventEnvelope,
) -> DomainEventOutbox:
    """Insert immutable outbox row — caller must commit in the same transaction."""
    get_event_contract_registry().validate_envelope(
        event_type=envelope.event_type,
        event_version=envelope.event_version,
        payload=envelope.payload,
    )
    row = DomainEventOutbox(
        event_id=envelope.event_id,
        event_type=envelope.event_type,
        event_version=envelope.event_version,
        aggregate_type=envelope.aggregate_type,
        aggregate_id=envelope.aggregate_id,
        tenant_id=envelope.tenant_id,
        company_id=envelope.company_id,
        payload=dict(envelope.payload),
        occurred_at=envelope.occurred_at,
        correlation_id=envelope.correlation_id,
        causation_id=envelope.causation_id,
        status="pending",
        attempt_count=0,
        available_at=_utcnow(),
    )
    db.add(row)
    await db.flush()
    logger.info(
        "domain_event.outbox.enqueued event_id=%s type=%s aggregate=%s:%s correlation=%s",
        envelope.event_id,
        envelope.event_type,
        envelope.aggregate_type,
        envelope.aggregate_id,
        envelope.correlation_id,
    )
    return row
