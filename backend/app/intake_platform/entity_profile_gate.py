"""Entity Profile compatibility gate for Form Definition (ADR-022 §7)."""

from __future__ import annotations

from fastapi import HTTPException

from backend.app.entity_profile.constants import SERVICE_SALES_MODULE
from backend.app.intake_platform.constants import (
    FORM_PURPOSES,
    SUBMISSION_POLICY_MODES,
    FormPurpose,
    SubmissionPolicyMode,
)
from backend.app.intake_platform.schemas import SubmissionPolicy


_SALES_ALLOWED_PURPOSES = {
    FormPurpose.questionnaire.value,
    FormPurpose.inquiry.value,
    FormPurpose.consent.value,
    FormPurpose.document_collection.value,
    FormPurpose.update.value,
}
_SALES_ALLOWED_MODES = {
    SubmissionPolicyMode.create.value,
    SubmissionPolicyMode.match_or_create.value,
    SubmissionPolicyMode.attach.value,
    SubmissionPolicyMode.review.value,
}

_RECRUITMENT_ALLOWED_PURPOSES = {
    FormPurpose.application.value,
    FormPurpose.questionnaire.value,
    FormPurpose.consent.value,
    FormPurpose.document_collection.value,
    FormPurpose.update.value,
}
_RECRUITMENT_ALLOWED_MODES = {
    SubmissionPolicyMode.create.value,
    SubmissionPolicyMode.match_or_create.value,
    SubmissionPolicyMode.attach.value,
    SubmissionPolicyMode.review.value,
}


def _entity_family(entity_profile_code: str) -> str:
    code = str(entity_profile_code or "").strip()
    if code.startswith(f"{SERVICE_SALES_MODULE}.") or code.startswith("service_sales."):
        return "sales"
    if code.startswith("recruitment."):
        return "recruitment"
    return "generic"


def validate_form_definition_triple(
    *,
    purpose: str,
    target_entity_profile_code: str,
    submission_policy: dict | SubmissionPolicy,
) -> None:
    p = str(purpose or "").strip()
    ep = str(target_entity_profile_code or "").strip()
    if not ep:
        raise HTTPException(status_code=422, detail={"code": "entity_profile_required", "message": "target_entity_profile_code is required"})
    if p not in FORM_PURPOSES:
        raise HTTPException(status_code=422, detail={"code": "invalid_purpose", "message": f"Invalid purpose: {p}"})

    policy = submission_policy if isinstance(submission_policy, SubmissionPolicy) else SubmissionPolicy.from_dict(submission_policy)
    mode = str(policy.mode or "").strip()
    if mode not in SUBMISSION_POLICY_MODES:
        raise HTTPException(status_code=422, detail={"code": "invalid_submission_policy_mode", "message": f"Invalid mode: {mode}"})

    family = _entity_family(ep)
    if family == "sales":
        if p not in _SALES_ALLOWED_PURPOSES:
            raise HTTPException(
                status_code=422,
                detail={"code": "purpose_not_allowed", "message": f"Purpose {p} not allowed for sales entity profile"},
            )
        if mode not in _SALES_ALLOWED_MODES:
            raise HTTPException(
                status_code=422,
                detail={"code": "policy_mode_not_allowed", "message": f"Mode {mode} not allowed for sales entity profile"},
            )
        if mode == SubmissionPolicyMode.match_or_create.value and policy.match_policy is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "match_policy_required", "message": "match_policy is required for match_or_create"},
            )
    elif family == "recruitment":
        if p not in _RECRUITMENT_ALLOWED_PURPOSES:
            raise HTTPException(
                status_code=422,
                detail={"code": "purpose_not_allowed", "message": f"Purpose {p} not allowed for recruitment entity profile"},
            )
        if mode not in _RECRUITMENT_ALLOWED_MODES:
            raise HTTPException(
                status_code=422,
                detail={"code": "policy_mode_not_allowed", "message": f"Mode {mode} not allowed for recruitment entity profile"},
            )

    if family == "recruitment" and ep.startswith(f"{SERVICE_SALES_MODULE}."):
        raise HTTPException(
            status_code=422,
            detail={"code": "incompatible_profile", "message": "Recruitment forms cannot use sales module profiles"},
        )
