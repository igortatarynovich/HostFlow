"""Form Definition read/write on TenantLeadForm (ADR-022)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.intake_platform.constants import (
    DEFAULT_INQUIRY_POLICY,
    DEFAULT_RECRUITMENT_APPLICATION_POLICY,
    DEFAULT_QUESTIONNAIRE_LANGUAGES,
    FORM_LIFECYCLE_STATUSES,
    FORM_PURPOSES,
    FormLifecycleStatus,
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
        "lifecycle_status": _normalize_lifecycle_status(getattr(form, "lifecycle_status", None)),
        "supported_languages": parse_supported_languages(getattr(form, "supported_languages", None)),
        "public_slug": str(getattr(form, "public_slug", None) or "") or None,
        "is_active": bool(form.is_active),
    }


def _normalize_lifecycle_status(value: Any) -> str:
    status = str(value or FormLifecycleStatus.active.value).strip()
    if status not in FORM_LIFECYCLE_STATUSES:
        return FormLifecycleStatus.active.value
    return status


def parse_supported_languages(value: Any) -> list[str]:
    raw = str(value or DEFAULT_QUESTIONNAIRE_LANGUAGES).strip().lower()
    langs = [part.strip() for part in raw.split(",") if part.strip()]
    out: list[str] = []
    for lang in langs:
        if lang in {"pl", "en", "ru"} and lang not in out:
            out.append(lang)
    return out or ["pl", "en", "ru"]


def format_supported_languages(languages: list[str]) -> str:
    normalized = parse_supported_languages(",".join(languages))
    return ",".join(normalized)


def apply_form_definition_fields(
    form: TenantLeadForm,
    *,
    purpose: Optional[str] = None,
    target_entity_profile_code: Optional[str] = None,
    submission_policy: Optional[dict[str, Any]] = None,
    published_version: Optional[int] = None,
    is_system_preset: Optional[bool] = None,
    lifecycle_status: Optional[str] = None,
    supported_languages: Optional[str] = None,
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
    if lifecycle_status is not None:
        form.lifecycle_status = _normalize_lifecycle_status(lifecycle_status)
    elif not getattr(form, "lifecycle_status", None):
        form.lifecycle_status = FormLifecycleStatus.active.value
    if supported_languages is not None:
        form.supported_languages = format_supported_languages(parse_supported_languages(supported_languages))
    elif not getattr(form, "supported_languages", None):
        form.supported_languages = DEFAULT_QUESTIONNAIRE_LANGUAGES
