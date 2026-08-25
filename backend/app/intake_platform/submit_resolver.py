"""Submit target resolution (ADR-022 Phase 1)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intake_platform.application_matcher import find_sales_inquiry_matches
from backend.app.intake_platform.constants import MatchConfidence, SubmissionPolicyMode
from backend.app.intake_platform.policy_resolver import policy_mode_requires_matching
from backend.app.intake_platform.schemas import EffectivePolicy, MatchResult, SubmitTargetResolution
from backend.app.models.lead import Lead


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _extract_identifiers(intake_state: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    contacts = _record(intake_state.get("contacts"))
    presentation = _record(intake_state.get("presentation_values"))
    if not presentation:
        presentation = _record(intake_state.get("presentation_values_v1"))
    email = contacts.get("email") or presentation.get("contact_email")
    phone = contacts.get("phone") or presentation.get("contact_phone")
    for key, value in presentation.items():
        if str(key).endswith(".contact_email") and value:
            email = email or value
        if str(key).endswith(".contact_phone") and value:
            phone = phone or value
    return (
        str(email).strip() if email else None,
        str(phone).strip() if phone else None,
    )


async def resolve_submit_target(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Lead,
    effective_policy: EffectivePolicy,
    intake_state: dict[str, Any],
) -> SubmitTargetResolution:
    mode = effective_policy.submission_policy.mode
    draft_id = str(draft_lead.id)

    if mode == SubmissionPolicyMode.attach.value:
        app_id = str(effective_policy.application_id or draft_id)
        return SubmitTargetResolution(target_lead_id=app_id, action="attach")

    if mode == SubmissionPolicyMode.create.value:
        return SubmitTargetResolution(target_lead_id=draft_id, action="create")

    if not policy_mode_requires_matching(effective_policy.submission_policy):
        return SubmitTargetResolution(target_lead_id=draft_id, action="create")

    match_policy = effective_policy.submission_policy.match_policy
    if match_policy is None:
        return SubmitTargetResolution(target_lead_id=draft_id, action="create")

    email, phone = _extract_identifiers(intake_state)
    match_result = await find_sales_inquiry_matches(
        db,
        tenant_id=str(tenant_id),
        email=email,
        phone=phone,
        entity_profile_code=effective_policy.target_entity_profile_code,
        match_policy=match_policy,
        exclude_lead_id=draft_id,
        publication_id=effective_policy.publication_id,
        intake_source_profile_id=effective_policy.publication_id,
    )

    auto_attach = (
        match_result.confidence == MatchConfidence.strong_single.value
        and match_result.suggested_action == "attach"
        and len(match_result.matched_application_ids) == 1
    )
    if auto_attach:
        target_id = match_result.matched_application_ids[0]
        return SubmitTargetResolution(
            target_lead_id=target_id,
            action="attach",
            match_result=match_result,
            draft_lead_abandoned=target_id != draft_id,
        )

    return SubmitTargetResolution(
        target_lead_id=draft_id,
        action="create",
        match_result=match_result,
    )


async def load_target_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> Optional[Lead]:
    lead = await db.get(Lead, str(lead_id))
    if lead is None or str(lead.tenant_id) != str(tenant_id):
        return None
    return lead
