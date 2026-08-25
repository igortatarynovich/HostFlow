"""Candidate → Activity Timeline (Stage 3E PR-2).

``CandidateCreated`` is emitted only from Lead→Candidate conversion when
Acquisition campaign stamp + a uniquely resolvable submission_id are present.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.acquisition.submission_routing import ACQUISITION_ROUTING_V1_KEY
from backend.app.intake_platform.submission_store import list_submissions
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    AcquisitionActivityEvent,
)
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead


def candidate_created_source_event_id(candidate_id: str) -> str:
    return f"acq.candidate.created:{str(candidate_id).strip()}"


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def read_acquisition_routing_stamp(lead: Lead) -> dict[str, Any]:
    return _record(_record(lead.normalized).get(ACQUISITION_ROUTING_V1_KEY))


def resolve_unique_submission_id(lead: Lead) -> str | None:
    """Return submission_id only when exactly one submission entry has an id."""
    ids: list[str] = []
    for entry in list_submissions(lead):
        sid = str(entry.get("submission_id") or "").strip()
        if sid:
            ids.append(sid)
    if len(ids) != 1:
        return None
    return ids[0]


async def record_candidate_created(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    candidate_id: str,
    lead_id: str,
    submission_id: str,
    route_intent: str | None = None,
    flight_id: str | None = None,
    actor_type: str = ACTOR_TYPE_SYSTEM,
    actor_id: str | None = None,
    occurred_at: datetime | None = None,
) -> AcquisitionActivityEvent:
    """Append ``CandidateCreated`` for an Acquisition-scoped conversion."""
    contract = get_activity_event_contract("CandidateCreated")
    if contract is None:
        raise RuntimeError("CandidateCreated missing from activity catalog")
    payload: dict[str, Any] = {
        "candidate_id": str(candidate_id).strip(),
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
        event_type="CandidateCreated",
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=candidate_created_source_event_id(candidate_id),
        occurred_at=occurred_at,
        provider=None,
    )


async def maybe_record_candidate_created_from_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    candidate: Candidate,
    actor_type: str = ACTOR_TYPE_SYSTEM,
    actor_id: str | None = None,
) -> AcquisitionActivityEvent | None:
    """Emit only with campaign stamp + uniquely resolvable submission_id.

    Call only after a new INSERT and successful ``lead.candidate_id`` flush.
    """
    stamp = read_acquisition_routing_stamp(lead)
    campaign_id = str(stamp.get("campaign_id") or "").strip()
    if not campaign_id:
        return None
    submission_id = resolve_unique_submission_id(lead)
    if not submission_id:
        return None
    candidate_id = str(getattr(candidate, "id", None) or "").strip()
    lead_id = str(getattr(lead, "id", None) or "").strip()
    if not candidate_id or not lead_id:
        return None
    flight_id = str(stamp.get("campaign_run_id") or "").strip() or None
    route_intent = str(stamp.get("route_intent") or "").strip() or None
    created_at = getattr(candidate, "created_at", None)
    occurred_at: datetime | None = None
    if isinstance(created_at, datetime):
        # Candidate.created_at is stored naive UTC in some schemas.
        occurred_at = (
            created_at
            if created_at.tzinfo is not None
            else created_at.replace(tzinfo=timezone.utc)
        )
    return await record_candidate_created(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        candidate_id=candidate_id,
        lead_id=lead_id,
        submission_id=submission_id,
        route_intent=route_intent,
        flight_id=flight_id,
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
    )


__all__ = [
    "candidate_created_source_event_id",
    "maybe_record_candidate_created_from_conversion",
    "read_acquisition_routing_stamp",
    "record_candidate_created",
    "resolve_unique_submission_id",
]
