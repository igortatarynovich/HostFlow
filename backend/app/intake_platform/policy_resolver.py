"""Effective Submission Policy resolver (ADR-022 §5)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intake_platform.constants import DEFAULT_INVITE_POLICY, SubmissionPolicyMode
from backend.app.intake_platform.form_definition import read_form_definition
from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite
from backend.app.models.tenant_lead_form import TenantLeadForm


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _publication_config(profile: Optional[IntakeSourceProfile]) -> dict[str, Any]:
    if profile is None:
        return {}
    raw = getattr(profile, "publication_config_v1", None)
    return _record(raw)


def _merge_policy(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    if not override:
        return dict(base)
    merged = dict(base)
    merged.update({k: v for k, v in override.items() if v is not None})
    if "match_policy" in override and isinstance(override["match_policy"], dict):
        mp = dict(merged.get("match_policy") or {})
        mp.update(override["match_policy"])
        merged["match_policy"] = mp
    return merged


async def resolve_effective_policy_for_publication(
    db: AsyncSession,
    *,
    tenant_id: str,
    form: TenantLeadForm,
    intake_profile: Optional[IntakeSourceProfile] = None,
) -> EffectivePolicy:
    _ = db, tenant_id
    definition = read_form_definition(form)
    base_policy = definition["submission_policy"]
    pub_cfg = _publication_config(intake_profile)
    policy_override = _record(pub_cfg.get("submission_policy_override"))
    effective_policy_dict = _merge_policy(base_policy, policy_override)
    source = {
        "provider": getattr(intake_profile, "provider", None) if intake_profile else None,
        "channel": getattr(intake_profile, "channel", None) if intake_profile else None,
        "campaign": pub_cfg.get("campaign"),
        "source_label": pub_cfg.get("source_label") or getattr(intake_profile, "source", None),
        "public_slug": getattr(intake_profile, "public_slug", None) if intake_profile else form.public_slug,
    }
    return EffectivePolicy(
        purpose=definition["purpose"],
        target_entity_profile_code=definition["target_entity_profile_code"],
        submission_policy=SubmissionPolicy.from_dict(effective_policy_dict),
        form_id=str(form.id),
        published_version=int(definition["published_version"] or 0),
        publication_id=str(intake_profile.id) if intake_profile is not None else None,
        source=source,
    )


def resolve_effective_policy_for_invite(
    *,
    form: Optional[TenantLeadForm],
    invite: LeadQuestionnaireInvite,
    entity_profile_code: str,
) -> EffectivePolicy:
    if form is not None:
        definition = read_form_definition(form)
        purpose = definition["purpose"]
        published_version = int(definition["published_version"] or 0)
        form_id = str(form.id)
        target_ep = definition["target_entity_profile_code"] or entity_profile_code
    else:
        purpose = "inquiry"
        published_version = 0
        form_id = str(invite.lead_form_id) if invite.lead_form_id else None
        target_ep = entity_profile_code

    policy = SubmissionPolicy.from_dict(DEFAULT_INVITE_POLICY)
    return EffectivePolicy(
        purpose=purpose,
        target_entity_profile_code=str(target_ep or entity_profile_code).strip(),
        submission_policy=policy,
        form_id=form_id,
        published_version=published_version,
        invite_id=str(invite.id),
        application_id=str(invite.lead_id),
        source={"entry": "questionnaire_invite", "invite_id": str(invite.id)},
    )


def policy_mode_requires_matching(policy: SubmissionPolicy) -> bool:
    return policy.mode == SubmissionPolicyMode.match_or_create.value
