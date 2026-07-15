"""Form Definition read/write on TenantLeadForm (ADR-022)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.intake_platform.constants import (
    DEFAULT_INQUIRY_POLICY,
    DEFAULT_RECRUITMENT_APPLICATION_POLICY,
    FORM_PURPOSES,
    FormPurpose,
)
from backend.app.intake_platform.schemas import SubmissionPolicy
from backend.app.models.tenant_lead_form import TenantLeadForm


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def default_purpose_for_entity_profile(entity_profile_code: str) -> str:
    code = str(entity_profile_code or "").strip()
    if code.startswith("recruitment."):
        return FormPurpose.application.value
    if code.startswith("service_sales."):
        return FormPurpose.inquiry.value
    return FormPurpose.inquiry.value


def default_submission_policy_for_entity_profile(entity_profile_code: str) -> dict[str, Any]:
    code = str(entity_profile_code or "").strip()
    if code.startswith("recruitment."):
        return dict(DEFAULT_RECRUITMENT_APPLICATION_POLICY)
    return dict(DEFAULT_INQUIRY_POLICY)


def read_form_definition(form: TenantLeadForm) -> dict[str, Any]:
    ep_code = str(getattr(form, "target_entity_profile_code", None) or "").strip()
    purpose = str(getattr(form, "purpose", None) or FormPurpose.inquiry.value).strip()
    if purpose not in FORM_PURPOSES:
        purpose = FormPurpose.inquiry.value
    policy_raw = getattr(form, "submission_policy", None)
    policy = SubmissionPolicy.from_dict(policy_raw if policy_raw else default_submission_policy_for_entity_profile(ep_code))
    return {
        "form_id": str(form.id),
        "title": str(form.title or ""),
        "purpose": purpose,
        "target_entity_profile_code": ep_code,
        "submission_policy": policy.to_dict(),
        "published_version": int(getattr(form, "published_version", None) or 0),
        "is_system_preset": bool(getattr(form, "is_system_preset", False)),
        "public_slug": str(getattr(form, "public_slug", None) or "") or None,
        "is_active": bool(form.is_active),
    }


def apply_form_definition_fields(
    form: TenantLeadForm,
    *,
    purpose: Optional[str] = None,
    target_entity_profile_code: Optional[str] = None,
    submission_policy: Optional[dict[str, Any]] = None,
    published_version: Optional[int] = None,
    is_system_preset: Optional[bool] = None,
) -> None:
    if target_entity_profile_code is not None:
        form.target_entity_profile_code = str(target_entity_profile_code).strip() or None
    ep = str(getattr(form, "target_entity_profile_code", None) or "").strip()
    if purpose is not None:
        form.purpose = str(purpose).strip()
    elif not getattr(form, "purpose", None):
        form.purpose = default_purpose_for_entity_profile(ep)
    if submission_policy is not None:
        form.submission_policy = dict(submission_policy)
    elif not getattr(form, "submission_policy", None):
        form.submission_policy = default_submission_policy_for_entity_profile(ep)
    if published_version is not None:
        form.published_version = int(published_version)
    elif getattr(form, "published_version", None) is None:
        form.published_version = 1
    if is_system_preset is not None:
        form.is_system_preset = bool(is_system_preset)
