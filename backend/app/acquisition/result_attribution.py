"""ADR-024 Stage 3D — automatic Result attribution from Universal Routing.

Attribution is derived **only** from ``acquisition_routing_v1`` stamped by Stage 3C.
Manual campaign/flight/endpoint links are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.submission_routing import (
    ACQUISITION_ROUTING_V1_KEY,
    RoutingDecisionStatus,
)
from backend.app.models.campaign import CampaignResultAttribution
from backend.app.models.lead import Lead

# Opaque result kinds — no FK into Operations tables.
RESULT_TYPE_INTAKE_LEAD = "intake_lead"
RESULT_TYPE_CANDIDATE = "candidate"
RESULT_TYPE_RECRUITMENT_APPLICATION = "recruitment_application"
RESULT_TYPE_SALES_INQUIRY = "sales_inquiry"

KNOWN_RESULT_TYPES = frozenset(
    {
        RESULT_TYPE_INTAKE_LEAD,
        RESULT_TYPE_CANDIDATE,
        RESULT_TYPE_RECRUITMENT_APPLICATION,
        RESULT_TYPE_SALES_INQUIRY,
    }
)


class AttributionError(ValueError):
    """Raised when attribution cannot be recorded without violating Stage 3D rules."""


@dataclass(frozen=True)
class AttributionSnapshot:
    campaign_id: str
    campaign_run_id: str
    submission_id: str
    lead_id: str
    result_type: str
    result_id: str
    route_intent: Optional[str]
    endpoint_form_id: Optional[str]
    endpoint_intake_source_profile_id: Optional[str]
    routing_source: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_run_id": self.campaign_run_id,
            "flight_id": self.campaign_run_id,
            "submission_id": self.submission_id,
            "lead_id": self.lead_id,
            "result_type": self.result_type,
            "result_id": self.result_id,
            "route_intent": self.route_intent,
            "endpoint_form_id": self.endpoint_form_id,
            "endpoint_intake_source_profile_id": self.endpoint_intake_source_profile_id,
            "routing_source": self.routing_source,
        }


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def read_routing_stamp(lead: Lead) -> dict[str, Any]:
    return _record(_record(lead.normalized).get(ACQUISITION_ROUTING_V1_KEY))


def resolve_result_identity(
    *,
    lead: Lead,
    created_candidate_id: Optional[str] = None,
    route_intent: Optional[str] = None,
) -> tuple[str, str]:
    """Pick opaque Result identity for Stage 3D without owning domain tables."""
    candidate_id = str(created_candidate_id or getattr(lead, "candidate_id", None) or "").strip()
    intent = str(route_intent or "").strip()
    if candidate_id:
        return RESULT_TYPE_CANDIDATE, candidate_id
    if intent == "sales_inquiry":
        return RESULT_TYPE_SALES_INQUIRY, str(lead.id)
    return RESULT_TYPE_INTAKE_LEAD, str(lead.id)


def build_attribution_from_routing(
    *,
    lead: Lead,
    submission_id: str,
    result_type: str,
    result_id: str,
) -> AttributionSnapshot:
    """Project attribution solely from the Lead routing stamp + submission id.

    Raises AttributionError if routing is missing, unresolved, or not campaign-attributed.
    """
    sub_id = str(submission_id or "").strip()
    if not sub_id:
        raise AttributionError("submission_id is required")

    rtype = str(result_type or "").strip()
    rid = str(result_id or "").strip()
    if not rtype or not rid:
        raise AttributionError("result_type and result_id are required")
    if rtype not in KNOWN_RESULT_TYPES:
        raise AttributionError(f"unknown result_type: {rtype}")

    stamp = read_routing_stamp(lead)
    if not stamp:
        raise AttributionError("acquisition_routing_v1 missing on Lead")

    status = str(stamp.get("status") or "").strip()
    if status != RoutingDecisionStatus.routed.value:
        raise AttributionError("attribution requires routed acquisition_routing_v1")

    campaign_id = str(stamp.get("campaign_id") or "").strip()
    campaign_run_id = str(stamp.get("campaign_run_id") or "").strip()
    if not campaign_id or not campaign_run_id:
        raise AttributionError("routed stamp missing campaign_id / campaign_run_id")

    return AttributionSnapshot(
        campaign_id=campaign_id,
        campaign_run_id=campaign_run_id,
        submission_id=sub_id,
        lead_id=str(lead.id),
        result_type=rtype,
        result_id=rid,
        route_intent=str(stamp.get("route_intent") or "").strip() or None,
        endpoint_form_id=str(stamp.get("form_id") or "").strip() or None,
        endpoint_intake_source_profile_id=str(stamp.get("intake_source_profile_id") or "").strip()
        or None,
        routing_source=str(stamp.get("source") or "").strip() or None,
    )


async def get_attribution_for_result(
    db: AsyncSession,
    *,
    tenant_id: str,
    result_type: str,
    result_id: str,
) -> Optional[CampaignResultAttribution]:
    row = await db.execute(
        select(CampaignResultAttribution).where(
            CampaignResultAttribution.tenant_id == str(tenant_id),
            CampaignResultAttribution.result_type == str(result_type),
            CampaignResultAttribution.result_id == str(result_id),
        )
    )
    return row.scalar_one_or_none()


async def get_attribution_for_submission(
    db: AsyncSession,
    *,
    tenant_id: str,
    submission_id: str,
) -> Optional[CampaignResultAttribution]:
    row = await db.execute(
        select(CampaignResultAttribution).where(
            CampaignResultAttribution.tenant_id == str(tenant_id),
            CampaignResultAttribution.submission_id == str(submission_id),
        )
    )
    return row.scalar_one_or_none()


def result_attributed_source_event_id(*, result_type: str, result_id: str) -> str:
    return f"acq.result.attributed:{str(result_type).strip()}:{str(result_id).strip()}"


async def _emit_result_attributed(
    db: AsyncSession,
    *,
    tenant_id: str,
    snapshot: AttributionSnapshot,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> None:
    """Stage 3E PR-2: Activity Timeline projection after attribution persist."""
    from backend.app.acquisition.activity.append_service import append_activity_event
    from backend.app.acquisition.activity.catalog import get_activity_event_contract
    from backend.app.models.acquisition_activity_event import ACTOR_TYPES

    contract = get_activity_event_contract("ResultAttributed")
    if contract is None:
        raise RuntimeError("ResultAttributed missing from activity catalog")
    actor = str(actor_type or "system").strip()
    if actor not in ACTOR_TYPES:
        actor = "system"
    await append_activity_event(
        db,
        tenant_id=str(tenant_id),
        campaign_id=snapshot.campaign_id,
        flight_id=snapshot.campaign_run_id,
        submission_id=snapshot.submission_id,
        result_id=snapshot.result_id,
        event_type="ResultAttributed",
        event_version=contract.event_version,
        payload={
            "result_type": snapshot.result_type,
            "result_id": snapshot.result_id,
        },
        actor_type=actor,
        actor_id=str(actor_id).strip() if actor_id else None,
        source_event_id=result_attributed_source_event_id(
            result_type=snapshot.result_type, result_id=snapshot.result_id
        ),
        provider=None,
    )


async def record_result_attribution_from_routing(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    submission_id: str,
    result_type: str,
    result_id: str,
    # Explicit kwargs accepted only to fail loudly if callers try manual override.
    campaign_id: Optional[str] = None,
    campaign_run_id: Optional[str] = None,
    flight_id: Optional[str] = None,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> CampaignResultAttribution:
    """Persist attribution from routing. Manual campaign/flight args are forbidden."""
    if campaign_id is not None or campaign_run_id is not None or flight_id is not None:
        raise AttributionError("manual attribution is forbidden; use routing stamp only")

    snapshot = build_attribution_from_routing(
        lead=lead,
        submission_id=submission_id,
        result_type=result_type,
        result_id=result_id,
    )

    existing = await get_attribution_for_result(
        db,
        tenant_id=str(tenant_id),
        result_type=snapshot.result_type,
        result_id=snapshot.result_id,
    )
    if existing is not None:
        _assert_same_attribution(existing, snapshot)
        await _emit_result_attributed(
            db,
            tenant_id=str(tenant_id),
            snapshot=snapshot,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return existing

    by_submission = await get_attribution_for_submission(
        db,
        tenant_id=str(tenant_id),
        submission_id=snapshot.submission_id,
    )
    if by_submission is not None:
        _assert_same_attribution(by_submission, snapshot)
        await _emit_result_attributed(
            db,
            tenant_id=str(tenant_id),
            snapshot=snapshot,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return by_submission

    row = CampaignResultAttribution(
        tenant_id=str(tenant_id),
        campaign_id=snapshot.campaign_id,
        campaign_run_id=snapshot.campaign_run_id,
        result_type=snapshot.result_type,
        result_id=snapshot.result_id,
        submission_id=snapshot.submission_id,
        lead_id=snapshot.lead_id,
        route_intent=snapshot.route_intent,
        endpoint_form_id=snapshot.endpoint_form_id,
        endpoint_intake_source_profile_id=snapshot.endpoint_intake_source_profile_id,
        routing_source=snapshot.routing_source,
    )
    db.add(row)
    await db.flush()
    await _emit_result_attributed(
        db,
        tenant_id=str(tenant_id),
        snapshot=snapshot,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return row


def _assert_same_attribution(existing: CampaignResultAttribution, snapshot: AttributionSnapshot) -> None:
    if (
        str(existing.campaign_id) != snapshot.campaign_id
        or str(existing.campaign_run_id) != snapshot.campaign_run_id
        or str(existing.submission_id) != snapshot.submission_id
        or str(existing.result_type) != snapshot.result_type
        or str(existing.result_id) != snapshot.result_id
    ):
        raise AttributionError("attribution conflict for existing result/submission")


async def try_record_result_attribution_from_routing(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    submission_id: str,
    created_candidate_id: Optional[str] = None,
) -> Optional[CampaignResultAttribution]:
    """Best-effort record after Decision Layer. No-op when routing is not campaign-attributed."""
    stamp = read_routing_stamp(lead)
    if str(stamp.get("status") or "") != RoutingDecisionStatus.routed.value:
        return None
    if not str(stamp.get("campaign_id") or "").strip():
        return None
    result_type, result_id = resolve_result_identity(
        lead=lead,
        created_candidate_id=created_candidate_id,
        route_intent=str(stamp.get("route_intent") or "") or None,
    )
    try:
        return await record_result_attribution_from_routing(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            submission_id=submission_id,
            result_type=result_type,
            result_id=result_id,
        )
    except AttributionError:
        return None
