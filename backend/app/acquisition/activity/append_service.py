"""Immutable append service for Acquisition Activity Timeline.

Public write surface for Stage 3E: **only** ``append_activity_event``.
PR-2 must call this (or project into it) — do not add specialized ``append_*`` wrappers.

Designed for transactional projection from domain operations / outbox consumers:
retries with the same ``(tenant_id, source_event_id)`` **return the existing row**.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.context_requirements import validate_event_context
from backend.app.acquisition.activity.errors import InvalidActivityActor
from backend.app.acquisition.activity.payloads import validate_activity_payload
from backend.app.acquisition.activity.repository import get_by_source_event_id
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPES,
    AcquisitionActivityEvent,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def append_activity_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    event_type: str,
    event_version: str,
    payload: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
    flight_id: str | None = None,
    endpoint_id: str | None = None,
    submission_id: str | None = None,
    result_id: str | None = None,
    outcome_id: str | None = None,
    actor_type: str,
    actor_id: str | None = None,
    provider: str | None = None,
    source_event_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
) -> AcquisitionActivityEvent:
    """Append one immutable activity event.

    Returns:
        The persisted ``AcquisitionActivityEvent``. On idempotent retry (same
        ``tenant_id`` + ``source_event_id``), returns the **existing** row
        (same ``id``) — never a void/None success.

    Contract notes for PR-2+:
    - No update/delete path.
    - ``occurred_at`` (fact time) vs ``recorded_at`` (persist time) are distinct;
      ``occurred_at`` is always materialised on the returned row.
    - ``event_type`` + ``event_version`` select the payload schema (per-type versions).
    - Safe inside the caller's transaction (race uses SAVEPOINT, not full rollback).
    """
    if not tenant_id or not str(tenant_id).strip():
        raise ValueError("tenant_id is required")
    if not campaign_id or not str(campaign_id).strip():
        raise ValueError("campaign_id is required")
    if actor_type not in ACTOR_TYPES:
        raise InvalidActivityActor(actor_type)

    body = dict(payload or {})
    validate_activity_payload(
        event_type=event_type,
        event_version=event_version,
        payload=body,
    )
    validate_event_context(
        event_type=event_type,
        flight_id=flight_id,
        endpoint_id=endpoint_id,
        submission_id=submission_id,
    )

    source_key = str(source_event_id).strip() if source_event_id else None
    if source_key == "":
        source_key = None

    if source_key is not None:
        existing = await get_by_source_event_id(
            db, tenant_id=tenant_id, source_event_id=source_key
        )
        if existing is not None:
            return existing

    fact_time = occurred_at or _utcnow()
    if fact_time.tzinfo is None:
        fact_time = fact_time.replace(tzinfo=timezone.utc)
    recorded = _utcnow()

    row = AcquisitionActivityEvent(
        id=str(uuid4()),
        tenant_id=str(tenant_id).strip(),
        campaign_id=str(campaign_id).strip(),
        flight_id=str(flight_id).strip() if flight_id else None,
        endpoint_id=str(endpoint_id).strip() if endpoint_id else None,
        submission_id=str(submission_id).strip() if submission_id else None,
        result_id=str(result_id).strip() if result_id else None,
        outcome_id=str(outcome_id).strip() if outcome_id else None,
        event_type=event_type,
        event_version=event_version,
        occurred_at=fact_time,
        recorded_at=recorded,
        actor_type=actor_type,
        actor_id=str(actor_id).strip() if actor_id else None,
        provider=str(provider).strip() if provider else None,
        source_event_id=source_key,
        correlation_id=str(correlation_id).strip() if correlation_id else None,
        causation_id=str(causation_id).strip() if causation_id else None,
        payload=body,
    )

    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError:
        if source_key is None:
            raise
        recovered = await get_by_source_event_id(
            db, tenant_id=tenant_id, source_event_id=source_key
        )
        if recovered is not None:
            return recovered
        raise

    return row


__all__ = ["append_activity_event"]
