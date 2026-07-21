"""Lead → Activity Timeline (Stage 3E PR-2).

``LeadCreated`` is emitted only when an Acquisition routing stamp with
``campaign_id`` is present on ``append_submission`` — never from ``create_lead``
or non-Acquisition intake paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    AcquisitionActivityEvent,
)
from backend.app.models.lead import Lead


def lead_created_source_event_id(lead_id: str) -> str:
    return f"acq.lead.created:{str(lead_id).strip()}"


async def record_lead_created(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    lead_id: str,
    submission_id: str,
    route_intent: str | None = None,
    flight_id: str | None = None,
    actor_type: str = ACTOR_TYPE_SYSTEM,
    actor_id: str | None = None,
    occurred_at: datetime | None = None,
) -> AcquisitionActivityEvent:
    """Append ``LeadCreated`` for an Acquisition-scoped Lead.

    ``occurred_at`` should be ``Lead.created_at`` (fact time of Lead birth).
    ``recorded_at`` is set by the append service to append time.
    """
    contract = get_activity_event_contract("LeadCreated")
    if contract is None:
        raise RuntimeError("LeadCreated missing from activity catalog")
    payload: dict[str, Any] = {
        "lead_id": str(lead_id).strip(),
        "submission_id": str(submission_id).strip(),
    }
    if route_intent and str(route_intent).strip():
        payload["route_intent"] = str(route_intent).strip()

    return await append_activity_event(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        flight_id=str(flight_id).strip() if flight_id else None,
        submission_id=str(submission_id).strip(),
        event_type="LeadCreated",
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=lead_created_source_event_id(lead_id),
        occurred_at=occurred_at,
        provider=None,
    )


async def maybe_record_lead_created_from_entry_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    submission_entry: Mapping[str, Any],
    entry_context: Mapping[str, Any] | None,
    actor_type: str = ACTOR_TYPE_SYSTEM,
    actor_id: str | None = None,
) -> AcquisitionActivityEvent | None:
    """Emit only when ``entry_context`` carries Acquisition routing with campaign_id."""
    ctx = dict(entry_context or {})
    routing = ctx.get("acquisition_routing_v1")
    if not isinstance(routing, Mapping):
        return None
    campaign_id = str(routing.get("campaign_id") or "").strip()
    if not campaign_id:
        return None
    submission_id = str(submission_entry.get("submission_id") or "").strip()
    if not submission_id:
        return None
    lead_id = str(getattr(lead, "id", None) or "").strip()
    if not lead_id:
        return None
    flight_id = str(routing.get("campaign_run_id") or "").strip() or None
    route_intent = str(routing.get("route_intent") or "").strip() or None
    created_at = getattr(lead, "created_at", None)
    occurred_at = created_at if isinstance(created_at, datetime) else None
    return await record_lead_created(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        submission_id=submission_id,
        route_intent=route_intent,
        flight_id=flight_id,
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
    )


__all__ = [
    "lead_created_source_event_id",
    "maybe_record_lead_created_from_entry_context",
    "record_lead_created",
]
