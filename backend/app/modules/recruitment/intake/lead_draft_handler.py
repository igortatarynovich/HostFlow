"""Recruitment-owned intake create path — domain Application result (R4).

Called only via Flights RecruitmentIntakePort adapter (R3.5).
Must not import Sales models/services/packages.

Acquisition stamp + submission append mirror Sales inquiry path so Marketing
Workspace counters / Activity Timeline observe candidate_application submits.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.result_attribution import try_record_result_attribution_from_routing
from backend.app.acquisition.submission_routing import (
    RoutingDecisionStatus,
    apply_unresolved_lead_disposition,
    resolve_universal_submission_routing,
    stamp_acquisition_routing_on_lead,
)
from backend.app.entity_profile.decision_layer import DecisionResult
from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
from backend.app.entity_profile.public_intake_draft_session import (
    get_public_intake_draft_block,
    submit_public_intake_lead_draft,
)
from backend.app.forms_platform.constants import HANDLER_RECRUITMENT_LEAD_DRAFT
from backend.app.intake_platform.destination_handler_contract import (
    RESULT_APPLICATION,
    DestinationHandlerResult,
)
from backend.app.intake_platform.destination_registry import DESTINATION_RECRUITMENT
from backend.app.intake_platform.policy_resolver import resolve_effective_policy_for_publication
from backend.app.intake_platform.schemas import EffectivePolicy
from backend.app.intake_platform.submission_store import append_submission
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.lead import Lead
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.leads.duplicate_resolution import LeadDuplicateMatch
from backend.app.modules.recruitment.services.application_result_service import (
    ensure_application_result_for_transport_lead,
)
from backend.app.services.outcome_resolver import resolve_outcomes

# Domain create path id (internal). Flights dispatcher id is applied by port adapter.
HANDLER_ID = HANDLER_RECRUITMENT_LEAD_DRAFT
ROUTE_INTENT = RouteIntent.candidate_application.value


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _empty_decision(*, route_intent: str = "unknown") -> DecisionResult:
    outcome = resolve_outcomes("unknown", "ingest")
    return DecisionResult(
        disposition="review_queue",
        outcome_resolution=outcome,
        duplicate_match=LeadDuplicateMatch(level="none", candidate=None, reasons=[], hr_blockers=[]),
        may_create_candidate=False,
        warnings=["acquisition_unresolved"],
        blocking_reasons=["acquisition_unresolved", str(route_intent or "unknown")],
    )


def _idempotency_key(lead: Lead, intake_state: dict[str, Any]) -> str:
    block = get_public_intake_draft_block(lead)
    token = str(block.get("intake_token") or "").strip()
    if token:
        return f"recruitment.application:{token}"
    return f"recruitment.application:lead:{lead.id}"


def _consent_metadata(intake_state: dict[str, Any]) -> dict[str, Any]:
    agreements = _record(intake_state.get("agreements"))
    return {
        "consents": agreements,
        "cookies_accepted": agreements.get("cookies_accepted"),
    }


async def _load_form_and_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_state: dict[str, Any],
) -> tuple[Optional[TenantLeadForm], Optional[IntakeSourceProfile]]:
    lf_meta = _record(intake_state.get("lead_form"))
    form_id = str(lf_meta.get("id") or "").strip() or None
    public_slug = str(lf_meta.get("public_slug") or "").strip() or None
    form: Optional[TenantLeadForm] = None
    if form_id:
        form = await db.get(TenantLeadForm, form_id)
        if form is not None and str(form.tenant_id) != str(tenant_id):
            form = None
    profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=form_id,
        public_slug=public_slug,
    )
    profile: Optional[IntakeSourceProfile] = None
    if profile_id:
        profile = await intake_crud.get_profile_by_id(
            db, tenant_id=str(tenant_id), profile_id=str(profile_id)
        )
    return form, profile


async def handle_candidate_application_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Lead,
    intake_state: dict[str, Any],
    presentation_code: Optional[str] = None,
    source: str = "public_intake",
) -> DestinationHandlerResult:
    """Recruitment destination handler for route_intent=candidate_application.

    Accepts only candidate_application. Never owns sales_inquiry / SalesInquiry.
    Stamps Acquisition routing and appends a submission so Activity Timeline /
    Marketing funnel observe the submit (parity with Sales inquiry path).
    """
    form, profile = await _load_form_and_profile(
        db, tenant_id=str(tenant_id), intake_state=intake_state
    )
    if form is None:
        from backend.app.intake_platform.constants import FormPurpose
        from backend.app.intake_platform.schemas import SubmissionPolicy

        effective: EffectivePolicy = EffectivePolicy(
            purpose=FormPurpose.application.value,
            target_entity_profile_code=str(intake_state.get("entity_profile_code") or ""),
            submission_policy=SubmissionPolicy.from_dict({"mode": "create"}),
        )
    else:
        effective = await resolve_effective_policy_for_publication(
            db,
            tenant_id=str(tenant_id),
            form=form,
            intake_profile=profile,
        )

    form_id = str(getattr(form, "id", None) or "").strip() or None
    profile_id = str(getattr(profile, "id", None) or "").strip() or None
    routing = await resolve_universal_submission_routing(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=profile_id,
        form_id=form_id,
    )
    routing_stamp = stamp_acquisition_routing_on_lead(draft_lead, routing)
    await db.flush()

    submission_entry = await append_submission(
        db,
        tenant_id=str(tenant_id),
        lead_id=str(draft_lead.id),
        effective_policy=effective,
        normalized_values=_record(intake_state.get("presentation_values"))
        or _record(intake_state.get("presentation_values_v1"))
        or intake_state,
        presentation_code=presentation_code,
        consent_metadata=_consent_metadata(intake_state),
        entry_context={
            "submit_action": "create",
            "acquisition_routing_v1": routing_stamp,
            "destination_handler_id": HANDLER_ID,
            "destination": DESTINATION_RECRUITMENT,
        },
        idempotency_key=_idempotency_key(draft_lead, intake_state),
    )

    if routing.status != RoutingDecisionStatus.routed.value:
        apply_unresolved_lead_disposition(draft_lead, routing)
        await db.flush()
        return DestinationHandlerResult(
            handler_id=HANDLER_ID,
            destination=DESTINATION_RECRUITMENT,
            route_intent=ROUTE_INTENT,
            result_entity_type=RESULT_APPLICATION,
            decision=_empty_decision(route_intent=routing.route_intent),
            created_candidate_id=None,
            transport_lead_id=str(draft_lead.id),
            effective_policy=effective,
            result_entity_id=None,
            result_created=False,
        )

    state = {**intake_state, "application_kind": "candidate"}
    decision, created_candidate_id = await submit_public_intake_lead_draft(
        db,
        tenant_id=str(tenant_id),
        lead=draft_lead,
        intake_state=state,
        source=source,
        route_intent_override=ROUTE_INTENT,
    )
    stamp_acquisition_routing_on_lead(draft_lead, routing)
    await try_record_result_attribution_from_routing(
        db,
        tenant_id=str(tenant_id),
        lead=draft_lead,
        submission_id=str(submission_entry.get("submission_id") or ""),
        created_candidate_id=created_candidate_id,
    )

    candidate_id = str(created_candidate_id or getattr(draft_lead, "candidate_id", None) or "").strip() or None
    result_entity_id: Optional[str] = None
    result_created = False
    if candidate_id:
        app = await ensure_application_result_for_transport_lead(
            db,
            tenant_id=str(tenant_id),
            lead=draft_lead,
            candidate_id=candidate_id,
            source=source,
            idempotency_key=_idempotency_key(draft_lead, state),
        )
        if app is not None:
            result_entity_id = str(app.id)
            result_created = True

    return DestinationHandlerResult(
        handler_id=HANDLER_ID,
        destination=DESTINATION_RECRUITMENT,
        route_intent=ROUTE_INTENT,
        result_entity_type=RESULT_APPLICATION,
        decision=decision,
        created_candidate_id=created_candidate_id,
        transport_lead_id=str(draft_lead.id),
        effective_policy=effective,
        result_entity_id=result_entity_id,
        result_created=result_created,
    )
