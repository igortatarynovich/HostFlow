"""Intake submit orchestration with ADR-022 policy (Phase 1)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
from backend.app.entity_profile.public_intake_draft_session import (
    PUBLIC_INTAKE_DRAFT_V1,
    get_public_intake_draft_block,
    submit_public_intake_lead_draft,
)
from backend.app.intake_platform.policy_resolver import resolve_effective_policy_for_publication
from backend.app.intake_platform.schemas import EffectivePolicy
from backend.app.intake_platform.submission_store import append_submission
from backend.app.intake_platform.submit_resolver import load_target_lead, resolve_submit_target
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import Lead
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.intake_routing import crud as intake_crud


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


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
        profile = await intake_crud.get_profile_by_id(db, tenant_id=str(tenant_id), profile_id=str(profile_id))
    return form, profile


def _consent_metadata(intake_state: dict[str, Any]) -> dict[str, Any]:
    agreements = _record(intake_state.get("agreements"))
    return {
        "consents": agreements,
        "cookies_accepted": agreements.get("cookies_accepted"),
    }


def _mark_draft_abandoned(draft_lead: Lead, *, target_lead_id: str, match_result: Any) -> None:
    normalized = _record(draft_lead.normalized)
    normalized["intake_submit_resolution_v1"] = {
        "status": "abandoned_draft",
        "merged_into_application_id": target_lead_id,
        "match_result": match_result.to_dict() if match_result is not None else None,
    }
    draft_lead.normalized = normalized
    draft_lead.stage = "intake_draft_abandoned"
    draft_lead.status = "duplicated"


def _submit_idempotency_key(draft_lead: Lead, intake_state: dict[str, Any]) -> str:
    block = get_public_intake_draft_block(draft_lead)
    token = str(block.get("intake_token") or "").strip()
    if token:
        return f"public-intake-submit:{token}"
    lf = _record(intake_state.get("lead_form"))
    form_id = str(lf.get("id") or "").strip()
    return f"public-intake-submit:{form_id}:{draft_lead.id}"


def _mark_inquiry_requires_manual_review(lead: Lead, match_result: Any) -> None:
    """Public intake could not auto-attach — flag for manager (no review queue in Product B v1)."""
    if match_result is None:
        return
    suggested = str(getattr(match_result, "suggested_action", "") or "").strip()
    if suggested != "review":
        return
    normalized = _record(lead.normalized)
    normalized["intake_review_required"] = True
    normalized["intake_review_message"] = (
        "Не удалось однозначно определить существующую заявку. "
        "Создана новая заявка, требующая проверки."
    )
    reasons = getattr(match_result, "reasons", None)
    if isinstance(reasons, list) and reasons:
        normalized["intake_review_reasons"] = list(reasons)
    lead.normalized = normalized
    if str(lead.stage or "").strip().lower() in {"", "new"}:
        lead.stage = "review_required"


async def submit_client_public_intake_with_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Lead,
    intake_state: dict[str, Any],
    presentation_code: Optional[str] = None,
    source: str = "public_intake",
) -> tuple[Any, Optional[str], EffectivePolicy]:
    """Run match_or_create resolution, append Submission, then Decision Layer on target Lead."""
    form, profile = await _load_form_and_profile(db, tenant_id=str(tenant_id), intake_state=intake_state)
    if form is None:
        from backend.app.intake_platform.constants import FormPurpose
        from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy

        effective = EffectivePolicy(
            purpose=FormPurpose.inquiry.value,
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

    resolution = await resolve_submit_target(
        db,
        tenant_id=str(tenant_id),
        draft_lead=draft_lead,
        effective_policy=effective,
        intake_state=intake_state,
    )
    target_lead = await load_target_lead(db, tenant_id=str(tenant_id), lead_id=resolution.target_lead_id)
    if target_lead is None:
        target_lead = draft_lead

    if resolution.draft_lead_abandoned and str(draft_lead.id) != str(target_lead.id):
        _mark_draft_abandoned(draft_lead, target_lead_id=str(target_lead.id), match_result=resolution.match_result)

    if (
        resolution.action == "create"
        and resolution.match_result is not None
        and str(getattr(resolution.match_result, "suggested_action", "") or "").strip() == "review"
        and str(target_lead.id) == str(draft_lead.id)
    ):
        _mark_inquiry_requires_manual_review(target_lead, resolution.match_result)

    decision, created_candidate_id = await submit_public_intake_lead_draft(
        db,
        tenant_id=str(tenant_id),
        lead=target_lead,
        intake_state=intake_state,
        source=source,
    )

    await append_submission(
        db,
        tenant_id=str(tenant_id),
        lead_id=str(target_lead.id),
        effective_policy=effective,
        normalized_values=_record(intake_state.get("presentation_values"))
        or _record(intake_state.get("presentation_values_v1"))
        or intake_state,
        presentation_code=presentation_code,
        consent_metadata=_consent_metadata(intake_state),
        match_result=resolution.match_result,
        entry_context={"submit_action": resolution.action},
        idempotency_key=_submit_idempotency_key(draft_lead, intake_state),
    )

    return decision, created_candidate_id, effective
