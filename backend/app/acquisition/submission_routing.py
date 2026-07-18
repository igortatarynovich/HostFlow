"""ADR-024 Stage 3C — Universal Submission Routing (Acquisition layer).

IntakeRouter remains Binding → Profile only. This module resolves optional
CampaignRun (Flight) via Form ∪ Profile associations and picks route_intent
from CampaignTarget (or profile default).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.campaign import (
    Campaign,
    CampaignRun,
    CampaignRunForm,
    CampaignRunIntakeSource,
    CampaignTarget,
)
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.intake_routing_enums import ROUTE_INTENTS, RouteIntent
from backend.app.models.lead import Lead
from backend.app.modules.intake_routing.reference import normalize_route_intent

ACQUISITION_ROUTING_V1_KEY = "acquisition_routing_v1"

ROUTING_ELIGIBLE_CAMPAIGN_STATUS = "active"
ROUTING_ELIGIBLE_FLIGHT_STATUS = "active"

# Intents that Stage 3C may auto-route into domain outcomes.
_ROUTABLE_INTENTS = frozenset(
    {
        RouteIntent.candidate_application.value,
        RouteIntent.sales_inquiry.value,
        RouteIntent.service_request.value,
        RouteIntent.partner_inquiry.value,
    }
)


class UnresolvedReason(str, Enum):
    no_intake_context = "no_intake_context"
    multiple_active_flights = "multiple_active_flights"
    form_profile_flight_conflict = "form_profile_flight_conflict"
    campaign_not_routable = "campaign_not_routable"
    flight_not_routable = "flight_not_routable"
    missing_primary_target = "missing_primary_target"
    multiple_primary_targets = "multiple_primary_targets"
    unknown_route_intent = "unknown_route_intent"
    unsupported_route_intent = "unsupported_route_intent"


UNRESOLVED_REASONS: frozenset[str] = frozenset(r.value for r in UnresolvedReason)


class RoutingDecisionStatus(str, Enum):
    routed = "routed"
    unresolved = "unresolved"


class RoutingSource(str, Enum):
    campaign_target = "campaign_target"
    profile_default = "profile_default"


@dataclass(frozen=True)
class UniversalRoutingDecision:
    status: str
    route_intent: str
    campaign_id: Optional[str] = None
    campaign_run_id: Optional[str] = None
    campaign_target_id: Optional[str] = None
    intake_source_profile_id: Optional[str] = None
    form_id: Optional[str] = None
    source: Optional[str] = None
    unresolved_reason: Optional[str] = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    decided_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "route_intent": self.route_intent,
            "campaign_id": self.campaign_id,
            "campaign_run_id": self.campaign_run_id,
            "campaign_target_id": self.campaign_target_id,
            "intake_source_profile_id": self.intake_source_profile_id,
            "form_id": self.form_id,
            "source": self.source,
            "unresolved_reason": self.unresolved_reason,
            "warnings": list(self.warnings),
            "decided_at": self.decided_at,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now(now: Optional[datetime] = None) -> str:
    return (now or _now()).isoformat()


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def is_flight_routing_eligible(
    *,
    association_is_active: bool,
    campaign_status: str,
    flight_status: str,
    starts_at: Optional[datetime],
    ends_at: Optional[datetime],
    at: Optional[datetime] = None,
) -> bool:
    """Single eligibility predicate for Stage 3C (Campaign=active, Flight=active)."""
    if not association_is_active:
        return False
    if str(campaign_status or "").strip().lower() != ROUTING_ELIGIBLE_CAMPAIGN_STATUS:
        return False
    if str(flight_status or "").strip().lower() != ROUTING_ELIGIBLE_FLIGHT_STATUS:
        return False
    moment = at or _now()
    if starts_at is not None:
        start = starts_at if starts_at.tzinfo else starts_at.replace(tzinfo=timezone.utc)
        if moment < start:
            return False
    if ends_at is not None:
        end = ends_at if ends_at.tzinfo else ends_at.replace(tzinfo=timezone.utc)
        if moment > end:
            return False
    return True


def _unresolved(
    *,
    reason: UnresolvedReason,
    route_intent: str = RouteIntent.unknown.value,
    intake_source_profile_id: Optional[str] = None,
    form_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    campaign_run_id: Optional[str] = None,
    campaign_target_id: Optional[str] = None,
    warnings: tuple[str, ...] = (),
    decided_at: Optional[str] = None,
) -> UniversalRoutingDecision:
    return UniversalRoutingDecision(
        status=RoutingDecisionStatus.unresolved.value,
        route_intent=normalize_route_intent(route_intent),
        campaign_id=campaign_id,
        campaign_run_id=campaign_run_id,
        campaign_target_id=campaign_target_id,
        intake_source_profile_id=intake_source_profile_id,
        form_id=form_id,
        source=None,
        unresolved_reason=reason.value,
        warnings=warnings,
        decided_at=decided_at or _iso_now(),
    )


def _routed(
    *,
    route_intent: str,
    source: RoutingSource,
    intake_source_profile_id: Optional[str] = None,
    form_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    campaign_run_id: Optional[str] = None,
    campaign_target_id: Optional[str] = None,
    warnings: tuple[str, ...] = (),
    decided_at: Optional[str] = None,
) -> UniversalRoutingDecision:
    return UniversalRoutingDecision(
        status=RoutingDecisionStatus.routed.value,
        route_intent=normalize_route_intent(route_intent),
        campaign_id=campaign_id,
        campaign_run_id=campaign_run_id,
        campaign_target_id=campaign_target_id,
        intake_source_profile_id=intake_source_profile_id,
        form_id=form_id,
        source=source.value,
        unresolved_reason=None,
        warnings=warnings,
        decided_at=decided_at or _iso_now(),
    )


def _classify_intent(raw: Any) -> tuple[str, Optional[UnresolvedReason]]:
    value = str(raw or "").strip().lower()
    if not value:
        return RouteIntent.unknown.value, UnresolvedReason.unknown_route_intent
    if value not in ROUTE_INTENTS and value not in {
        "candidate",
        "client_lead",
        "service_order_lead",
        "partner_lead",
    }:
        return RouteIntent.unknown.value, UnresolvedReason.unsupported_route_intent
    intent = normalize_route_intent(value)
    if intent == RouteIntent.unknown.value:
        return intent, UnresolvedReason.unknown_route_intent
    if intent not in _ROUTABLE_INTENTS:
        return intent, UnresolvedReason.unsupported_route_intent
    return intent, None


async def _eligible_form_flights(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    at: datetime,
) -> set[str]:
    rows = (
        await db.execute(
            select(CampaignRunForm, CampaignRun, Campaign)
            .join(CampaignRun, CampaignRun.id == CampaignRunForm.campaign_run_id)
            .join(Campaign, Campaign.id == CampaignRun.campaign_id)
            .where(
                CampaignRunForm.tenant_id == str(tenant_id),
                CampaignRunForm.form_id == str(form_id),
                CampaignRunForm.is_active.is_(True),
            )
        )
    ).all()
    out: set[str] = set()
    for link, flight, campaign in rows:
        if is_flight_routing_eligible(
            association_is_active=bool(link.is_active),
            campaign_status=str(campaign.status or ""),
            flight_status=str(flight.status or ""),
            starts_at=flight.starts_at,
            ends_at=flight.ends_at,
            at=at,
        ):
            out.add(str(flight.id))
    return out


async def _eligible_profile_flights(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: str,
    at: datetime,
) -> set[str]:
    rows = (
        await db.execute(
            select(CampaignRunIntakeSource, CampaignRun, Campaign)
            .join(CampaignRun, CampaignRun.id == CampaignRunIntakeSource.campaign_run_id)
            .join(Campaign, Campaign.id == CampaignRun.campaign_id)
            .where(
                CampaignRunIntakeSource.tenant_id == str(tenant_id),
                CampaignRunIntakeSource.intake_source_profile_id == str(profile_id),
                CampaignRunIntakeSource.is_active.is_(True),
            )
        )
    ).all()
    out: set[str] = set()
    for link, flight, campaign in rows:
        if is_flight_routing_eligible(
            association_is_active=bool(link.is_active),
            campaign_status=str(campaign.status or ""),
            flight_status=str(flight.status or ""),
            starts_at=flight.starts_at,
            ends_at=flight.ends_at,
            at=at,
        ):
            out.add(str(flight.id))
    return out


async def _decision_from_flight(
    db: AsyncSession,
    *,
    tenant_id: str,
    flight_id: str,
    intake_source_profile_id: Optional[str],
    form_id: Optional[str],
    decided_at: str,
) -> UniversalRoutingDecision:
    flight = await db.get(CampaignRun, str(flight_id))
    if flight is None or str(flight.tenant_id) != str(tenant_id):
        return _unresolved(
            reason=UnresolvedReason.flight_not_routable,
            intake_source_profile_id=intake_source_profile_id,
            form_id=form_id,
            campaign_run_id=str(flight_id),
            warnings=("flight_missing",),
            decided_at=decided_at,
        )
    campaign = await db.get(Campaign, str(flight.campaign_id))
    if campaign is None or str(campaign.tenant_id) != str(tenant_id):
        return _unresolved(
            reason=UnresolvedReason.campaign_not_routable,
            intake_source_profile_id=intake_source_profile_id,
            form_id=form_id,
            campaign_run_id=str(flight.id),
            warnings=("campaign_missing",),
            decided_at=decided_at,
        )
    if str(campaign.status or "").strip().lower() != ROUTING_ELIGIBLE_CAMPAIGN_STATUS:
        return _unresolved(
            reason=UnresolvedReason.campaign_not_routable,
            intake_source_profile_id=intake_source_profile_id,
            form_id=form_id,
            campaign_id=str(campaign.id),
            campaign_run_id=str(flight.id),
            warnings=(f"campaign_status:{campaign.status}",),
            decided_at=decided_at,
        )
    if str(flight.status or "").strip().lower() != ROUTING_ELIGIBLE_FLIGHT_STATUS:
        return _unresolved(
            reason=UnresolvedReason.flight_not_routable,
            intake_source_profile_id=intake_source_profile_id,
            form_id=form_id,
            campaign_id=str(campaign.id),
            campaign_run_id=str(flight.id),
            warnings=(f"flight_status:{flight.status}",),
            decided_at=decided_at,
        )

    targets = (
        await db.execute(
            select(CampaignTarget).where(
                CampaignTarget.tenant_id == str(tenant_id),
                CampaignTarget.campaign_id == str(campaign.id),
                CampaignTarget.role == "primary",
            )
        )
    ).scalars().all()
    if not targets:
        return _unresolved(
            reason=UnresolvedReason.missing_primary_target,
            intake_source_profile_id=intake_source_profile_id,
            form_id=form_id,
            campaign_id=str(campaign.id),
            campaign_run_id=str(flight.id),
            decided_at=decided_at,
        )
    if len(targets) > 1:
        return _unresolved(
            reason=UnresolvedReason.multiple_primary_targets,
            intake_source_profile_id=intake_source_profile_id,
            form_id=form_id,
            campaign_id=str(campaign.id),
            campaign_run_id=str(flight.id),
            warnings=(f"primary_target_count:{len(targets)}",),
            decided_at=decided_at,
        )

    target = targets[0]
    intent, intent_reason = _classify_intent(target.route_intent)
    if intent_reason is not None:
        return _unresolved(
            reason=intent_reason,
            route_intent=intent,
            intake_source_profile_id=intake_source_profile_id,
            form_id=form_id,
            campaign_id=str(campaign.id),
            campaign_run_id=str(flight.id),
            campaign_target_id=str(target.id),
            decided_at=decided_at,
        )
    return _routed(
        route_intent=intent,
        source=RoutingSource.campaign_target,
        intake_source_profile_id=intake_source_profile_id,
        form_id=form_id,
        campaign_id=str(campaign.id),
        campaign_run_id=str(flight.id),
        campaign_target_id=str(target.id),
        decided_at=decided_at,
    )


async def _profile_default_decision(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: Optional[str],
    form_id: Optional[str],
    decided_at: str,
) -> UniversalRoutingDecision:
    if not profile_id:
        return _unresolved(
            reason=UnresolvedReason.no_intake_context,
            form_id=form_id,
            decided_at=decided_at,
            warnings=("no_profile_for_default_routing",),
        )
    profile = await db.get(IntakeSourceProfile, str(profile_id))
    if profile is None or str(profile.tenant_id) != str(tenant_id):
        return _unresolved(
            reason=UnresolvedReason.no_intake_context,
            intake_source_profile_id=str(profile_id),
            form_id=form_id,
            decided_at=decided_at,
            warnings=("profile_missing",),
        )
    intent, intent_reason = _classify_intent(profile.route_intent)
    if intent_reason is not None:
        return _unresolved(
            reason=intent_reason,
            route_intent=intent,
            intake_source_profile_id=str(profile.id),
            form_id=form_id,
            decided_at=decided_at,
        )
    return _routed(
        route_intent=intent,
        source=RoutingSource.profile_default,
        intake_source_profile_id=str(profile.id),
        form_id=form_id,
        decided_at=decided_at,
    )


async def resolve_universal_submission_routing(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_source_profile_id: Optional[str] = None,
    form_id: Optional[str] = None,
    at: Optional[datetime] = None,
) -> UniversalRoutingDecision:
    """Form ∪ Profile Flight matrix → CampaignTarget.route_intent or profile default."""
    moment = at or _now()
    decided_at = _iso_now(moment)
    profile_id = str(intake_source_profile_id or "").strip() or None
    form = str(form_id or "").strip() or None

    if not profile_id and not form:
        return _unresolved(
            reason=UnresolvedReason.no_intake_context,
            decided_at=decided_at,
        )

    form_flights: set[str] = set()
    profile_flights: set[str] = set()
    if form:
        form_flights = await _eligible_form_flights(
            db, tenant_id=str(tenant_id), form_id=form, at=moment
        )
    if profile_id:
        profile_flights = await _eligible_profile_flights(
            db, tenant_id=str(tenant_id), profile_id=profile_id, at=moment
        )

    if len(form_flights) > 1 or len(profile_flights) > 1:
        return _unresolved(
            reason=UnresolvedReason.multiple_active_flights,
            intake_source_profile_id=profile_id,
            form_id=form,
            warnings=(
                f"form_flights:{len(form_flights)}",
                f"profile_flights:{len(profile_flights)}",
            ),
            decided_at=decided_at,
        )

    if form_flights and profile_flights and form_flights != profile_flights:
        return _unresolved(
            reason=UnresolvedReason.form_profile_flight_conflict,
            intake_source_profile_id=profile_id,
            form_id=form,
            warnings=(
                f"form_flight:{next(iter(form_flights))}",
                f"profile_flight:{next(iter(profile_flights))}",
            ),
            decided_at=decided_at,
        )

    chosen: Optional[str] = None
    if form_flights:
        chosen = next(iter(form_flights))
    elif profile_flights:
        chosen = next(iter(profile_flights))

    if chosen is not None:
        return await _decision_from_flight(
            db,
            tenant_id=str(tenant_id),
            flight_id=chosen,
            intake_source_profile_id=profile_id,
            form_id=form,
            decided_at=decided_at,
        )

    return await _profile_default_decision(
        db,
        tenant_id=str(tenant_id),
        profile_id=profile_id,
        form_id=form,
        decided_at=decided_at,
    )


def stamp_acquisition_routing_on_lead(
    lead: Lead,
    decision: UniversalRoutingDecision,
) -> dict[str, Any]:
    """Write ``acquisition_routing_v1`` onto Lead.normalized (in-memory + flag)."""
    normalized = _record(lead.normalized)
    block = decision.to_dict()
    normalized[ACQUISITION_ROUTING_V1_KEY] = block
    lead.normalized = normalized
    flag_modified(lead, "normalized")
    return block


def apply_unresolved_lead_disposition(lead: Lead, decision: UniversalRoutingDecision) -> None:
    """Mark Lead as needs_routing without creating domain Results."""
    stamp_acquisition_routing_on_lead(lead, decision)
    lead.status = "needs_routing"
    lead.error = decision.unresolved_reason or UnresolvedReason.unknown_route_intent.value
