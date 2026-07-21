"""Flight lifecycle transitions + Activity Timeline instrumentation (Stage 3E PR-2).

Sole write choke-point for ``CampaignRun.status`` changes. Call sites must use
these helpers — not mutate ``flight.status`` ad hoc and not emit from HTTP handlers.

``FlightFailed`` is wired in the transition table but has **no** production caller
until a confirmed failure path exists (do not invent one here).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.acquisition.activity.repository import get_by_source_event_id
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    AcquisitionActivityEvent,
)
from backend.app.models.campaign import CampaignRun

FLIGHT_STATUS_PLANNED = "planned"
FLIGHT_STATUS_ACTIVE = "active"
FLIGHT_STATUS_PAUSED = "paused"
FLIGHT_STATUS_COMPLETED = "completed"
FLIGHT_STATUS_FAILED = "failed"

FLIGHT_LIFECYCLE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "FlightCreated",
        "FlightStarted",
        "FlightPaused",
        "FlightResumed",
        "FlightCompleted",
        "FlightFailed",
    }
)

# Existing status vocabulary only — no new statuses.
# FlightFailed intentionally omitted: no confirmed production failure transition yet.
_TRANSITIONS: dict[tuple[str, str], str] = {
    (FLIGHT_STATUS_PLANNED, FLIGHT_STATUS_ACTIVE): "FlightStarted",
    (FLIGHT_STATUS_ACTIVE, FLIGHT_STATUS_PAUSED): "FlightPaused",
    (FLIGHT_STATUS_PAUSED, FLIGHT_STATUS_ACTIVE): "FlightResumed",
    (FLIGHT_STATUS_ACTIVE, FLIGHT_STATUS_COMPLETED): "FlightCompleted",
}


class FlightLifecycleError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def flight_lifecycle_source_event_id(flight_id: str, seq: int) -> str:
    """Deterministic idempotency key for the N-th lifecycle transition of a Flight."""
    return f"acq.flight.lifecycle:{flight_id}:{seq}"


def _norm_status(value: str) -> str:
    return str(value or "").strip().lower()


async def _lifecycle_event_count(
    db: AsyncSession, *, tenant_id: str, flight_id: str
) -> int:
    stmt = select(func.count()).select_from(AcquisitionActivityEvent).where(
        AcquisitionActivityEvent.tenant_id == str(tenant_id),
        AcquisitionActivityEvent.flight_id == str(flight_id),
        AcquisitionActivityEvent.event_type.in_(FLIGHT_LIFECYCLE_EVENT_TYPES),
    )
    return int((await db.execute(stmt)).scalar_one())


def _build_payload(
    *,
    previous_status: str | None,
    new_status: str,
    reason: str | None,
    event_type: str,
) -> dict[str, Any]:
    body: dict[str, Any] = {"new_status": new_status}
    if previous_status is not None:
        body["previous_status"] = previous_status
    if reason is not None and str(reason).strip():
        reason_s = str(reason).strip()
        if event_type == "FlightFailed":
            body["reason_code"] = reason_s
        else:
            body["reason"] = reason_s
    return body


async def _emit_lifecycle_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    event_type: str,
    payload: dict[str, Any],
    source_event_id: str,
    actor_type: str,
    actor_id: str | None,
    occurred_at: datetime | None,
) -> AcquisitionActivityEvent:
    contract = get_activity_event_contract(event_type)
    if contract is None:
        raise FlightLifecycleError(f"unknown lifecycle event_type: {event_type!r}")
    return await append_activity_event(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        event_type=event_type,
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=source_event_id,
        occurred_at=occurred_at,
        # No provider-specific fields on Flight lifecycle events.
        provider=None,
    )


async def create_flight(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str | None = None,
    code: str = "flight_1",
    name: str = "Flight 1",
    actor_type: str = ACTOR_TYPE_SYSTEM,
    actor_id: str | None = None,
    occurred_at: datetime | None = None,
    reason: str | None = None,
) -> tuple[CampaignRun, AcquisitionActivityEvent]:
    """Persist a new Flight in ``planned`` and append ``FlightCreated`` in-tx."""
    fid = str(flight_id or uuid4())
    flight = CampaignRun(
        id=fid,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        code=code,
        name=name,
        status=FLIGHT_STATUS_PLANNED,
    )
    db.add(flight)
    await db.flush()

    source_event_id = flight_lifecycle_source_event_id(fid, 1)
    event = await _emit_lifecycle_event(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        flight_id=fid,
        event_type="FlightCreated",
        payload=_build_payload(
            previous_status=None,
            new_status=FLIGHT_STATUS_PLANNED,
            reason=reason,
            event_type="FlightCreated",
        ),
        source_event_id=source_event_id,
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
    )
    return flight, event


async def transition_flight_status(
    db: AsyncSession,
    *,
    flight: CampaignRun,
    new_status: str,
    actor_type: str,
    actor_id: str | None = None,
    reason: str | None = None,
    occurred_at: datetime | None = None,
) -> AcquisitionActivityEvent:
    """Apply an allowed Flight status transition and append the matching event.

    Emits only after the in-memory status change is applied; caller owns commit.
    Rollback of the surrounding transaction drops both status change and event.

    Retry when the Flight is already at ``new_status`` returns the existing
    lifecycle event for the current sequence (same ``source_event_id``).
    """
    previous = _norm_status(flight.status)
    target = _norm_status(new_status)
    if not target:
        raise FlightLifecycleError("new_status is required")

    seq = await _lifecycle_event_count(
        db, tenant_id=flight.tenant_id, flight_id=flight.id
    )

    if previous == target:
        if seq < 1:
            raise FlightLifecycleError(
                f"flight {flight.id} already at {target!r} but has no lifecycle events"
            )
        source_event_id = flight_lifecycle_source_event_id(flight.id, seq)
        existing = await get_by_source_event_id(
            db, tenant_id=flight.tenant_id, source_event_id=source_event_id
        )
        if existing is None:
            raise FlightLifecycleError(
                f"missing lifecycle event for idempotent retry: {source_event_id}"
            )
        return existing

    event_type = _TRANSITIONS.get((previous, target))
    if event_type is None:
        raise FlightLifecycleError(
            f"unsupported flight transition {previous!r} -> {target!r}"
        )

    source_event_id = flight_lifecycle_source_event_id(flight.id, seq + 1)
    # Status first — append shares the same transaction.
    flight.status = target
    await db.flush()

    return await _emit_lifecycle_event(
        db,
        tenant_id=str(flight.tenant_id),
        campaign_id=str(flight.campaign_id),
        flight_id=str(flight.id),
        event_type=event_type,
        payload=_build_payload(
            previous_status=previous,
            new_status=target,
            reason=reason,
            event_type=event_type,
        ),
        source_event_id=source_event_id,
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
    )


__all__ = [
    "FLIGHT_LIFECYCLE_EVENT_TYPES",
    "FLIGHT_STATUS_ACTIVE",
    "FLIGHT_STATUS_COMPLETED",
    "FLIGHT_STATUS_FAILED",
    "FLIGHT_STATUS_PAUSED",
    "FLIGHT_STATUS_PLANNED",
    "FlightLifecycleError",
    "create_flight",
    "flight_lifecycle_source_event_id",
    "transition_flight_status",
]
