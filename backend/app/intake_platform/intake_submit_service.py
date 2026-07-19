"""Intake submit orchestration with ADR-022 policy (Phase 1) + ADR-024 Stage 3C.

Runtime Split R3: destination dispatch owns Recruitment vs Sales handlers.
`application_kind` is a derived label only — never the routing SoT.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
from backend.app.forms_platform.errors import FormsRoutingUnresolvedError
from backend.app.intake_platform.destination_handler_contract import DestinationHandlerResult
from backend.app.intake_platform.destination_registry import DestinationMissingHandlerError
from backend.app.intake_platform.handler_dispatch import dispatch_destination_submit
from backend.app.intake_platform.schemas import EffectivePolicy
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import Lead
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.intake_routing.reference import normalize_route_intent


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


async def resolve_pinned_route_intent_for_submit(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_state: dict[str, Any],
) -> str:
    """Pinned Source Profile route_intent — fail-closed when missing/unknown."""
    lf_meta = _record(intake_state.get("lead_form"))
    form_id = str(lf_meta.get("id") or "").strip() or None
    public_slug = str(lf_meta.get("public_slug") or "").strip() or None
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
    raw = str(getattr(profile, "route_intent", None) or "").strip() if profile is not None else ""
    if not raw:
        raise FormsRoutingUnresolvedError(
            details={"reason": "missing_route_intent"},
            message="Intake source profile with explicit route_intent is required",
        )
    intent = normalize_route_intent(raw)
    if intent in {"", "unknown"}:
        raise FormsRoutingUnresolvedError(
            details={"reason": "unknown_route_intent", "route_intent": raw},
            message="route_intent is unknown (fail-closed)",
        )
    return intent


async def dispatch_public_intake_submit(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Lead,
    intake_state: dict[str, Any],
    presentation_code: Optional[str] = None,
    source: str = "public_intake",
    route_intent: str | None = None,
) -> DestinationHandlerResult:
    """Resolve pinned intent (or explicit override) and dispatch to one destination handler."""
    intent = str(route_intent or "").strip() or await resolve_pinned_route_intent_for_submit(
        db, tenant_id=str(tenant_id), intake_state=intake_state
    )
    try:
        return await dispatch_destination_submit(
            db,
            route_intent=intent,
            tenant_id=str(tenant_id),
            draft_lead=draft_lead,
            intake_state=intake_state,
            presentation_code=presentation_code,
            source=source,
        )
    except DestinationMissingHandlerError as exc:
        raise FormsRoutingUnresolvedError(
            details=dict(exc.details),
            message=exc.message,
        ) from exc


async def submit_client_public_intake_with_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Lead,
    intake_state: dict[str, Any],
    presentation_code: Optional[str] = None,
    source: str = "public_intake",
) -> tuple[Any, Optional[str], EffectivePolicy]:
    """Compatibility wrapper → Sales-owned sales.inquiry_draft handler (R3)."""
    from backend.app.models.intake_routing_enums import RouteIntent

    result = await dispatch_public_intake_submit(
        db,
        tenant_id=str(tenant_id),
        draft_lead=draft_lead,
        intake_state=intake_state,
        presentation_code=presentation_code,
        source=source,
        route_intent=RouteIntent.sales_inquiry.value,
    )
    effective = result.effective_policy
    if effective is None:
        from backend.app.intake_platform.constants import FormPurpose
        from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy

        effective = EffectivePolicy(
            purpose=FormPurpose.inquiry.value,
            target_entity_profile_code=str(intake_state.get("entity_profile_code") or ""),
            submission_policy=SubmissionPolicy.from_dict({"mode": "create"}),
        )
    return result.decision, result.created_candidate_id, effective


async def submit_candidate_public_intake_with_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Lead,
    intake_state: dict[str, Any],
    presentation_code: Optional[str] = None,
    source: str = "public_intake",
) -> tuple[Any, Optional[str]]:
    """Compatibility wrapper → Recruitment-owned recruitment.lead_draft handler (R3)."""
    from backend.app.models.intake_routing_enums import RouteIntent

    result = await dispatch_public_intake_submit(
        db,
        tenant_id=str(tenant_id),
        draft_lead=draft_lead,
        intake_state=intake_state,
        presentation_code=presentation_code,
        source=source,
        route_intent=RouteIntent.candidate_application.value,
    )
    return result.decision, result.created_candidate_id


# Re-export for tests that patch the former direct import path.
async def submit_public_intake_lead_draft(*args: Any, **kwargs: Any):  # noqa: ANN401
    from backend.app.entity_profile.public_intake_draft_session import (
        submit_public_intake_lead_draft as _impl,
    )

    return await _impl(*args, **kwargs)
