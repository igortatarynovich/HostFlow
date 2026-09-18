"""Published Workforce ORM types (read/write surface for Employment continuity)."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "FIELD_STATUS_APPROVE_OK": ("backend.app.models.workforce_hr_verified_field", "FIELD_STATUS_APPROVE_OK"),
    "FIELD_STATUS_CONFLICT": ("backend.app.models.workforce_hr_verified_field", "FIELD_STATUS_CONFLICT"),
    "FIELD_STATUS_OVERRIDDEN": ("backend.app.models.workforce_hr_verified_field", "FIELD_STATUS_OVERRIDDEN"),
    "FIELD_STATUS_PENDING": ("backend.app.models.workforce_hr_verified_field", "FIELD_STATUS_PENDING"),
    "FIELD_STATUS_VERIFIED": ("backend.app.models.workforce_hr_verified_field", "FIELD_STATUS_VERIFIED"),
    "HR_REVIEW_STATUS_APPROVED": ("backend.app.models.workforce_hr_review", "HR_REVIEW_STATUS_APPROVED"),
    "HR_REVIEW_STATUS_REJECTED": ("backend.app.models.workforce_hr_review", "HR_REVIEW_STATUS_REJECTED"),
    "HR_REVIEW_STATUS_RETURNED": ("backend.app.models.workforce_hr_review", "HR_REVIEW_STATUS_RETURNED"),
    "HR_REVIEW_STATUS_WAITING_DOCUMENTS": (
        "backend.app.models.workforce_hr_review",
        "HR_REVIEW_STATUS_WAITING_DOCUMENTS",
    ),
    "HR_REVIEW_STATUS_WAITING_PAYMENTS": (
        "backend.app.models.workforce_hr_review",
        "HR_REVIEW_STATUS_WAITING_PAYMENTS",
    ),
    "HR_REVIEW_STATUS_WAITING_RED_PAPER": (
        "backend.app.models.workforce_hr_review",
        "HR_REVIEW_STATUS_WAITING_RED_PAPER",
    ),
    "HR_REVIEW_STATUS_WAITING_WORK_PERMIT": (
        "backend.app.models.workforce_hr_review",
        "HR_REVIEW_STATUS_WAITING_WORK_PERMIT",
    ),
    "HR_REVIEW_TERMINAL_STATUSES": ("backend.app.models.workforce_hr_review", "HR_REVIEW_TERMINAL_STATUSES"),
    "VERIFICATION_NEEDS_CORRECTION": (
        "backend.app.models.workforce_hr_document_verification",
        "VERIFICATION_NEEDS_CORRECTION",
    ),
    "VERIFICATION_NOT_REQUIRED": (
        "backend.app.models.workforce_hr_document_verification",
        "VERIFICATION_NOT_REQUIRED",
    ),
    "VERIFICATION_OPENED": ("backend.app.models.workforce_hr_document_verification", "VERIFICATION_OPENED"),
    "VERIFICATION_PENDING": ("backend.app.models.workforce_hr_document_verification", "VERIFICATION_PENDING"),
    "VERIFICATION_REJECTED": ("backend.app.models.workforce_hr_document_verification", "VERIFICATION_REJECTED"),
    "VERIFICATION_TERMINAL_OK": (
        "backend.app.models.workforce_hr_document_verification",
        "VERIFICATION_TERMINAL_OK",
    ),
    "VERIFICATION_VERIFIED": ("backend.app.models.workforce_hr_document_verification", "VERIFICATION_VERIFIED"),
    "WorkforceComplianceState": ("backend.app.models.workforce_compliance_state", "WorkforceComplianceState"),
    "WorkforceEmployee": ("backend.app.models.workforce_employee", "WorkforceEmployee"),
    "WorkforceHrDocumentContext": (
        "backend.app.models.workforce_hr_document_context",
        "WorkforceHrDocumentContext",
    ),
    "WorkforceHrDocumentControlTask": (
        "backend.app.models.workforce_hr_document_control_task",
        "WorkforceHrDocumentControlTask",
    ),
    "WorkforceHrDocumentVerification": (
        "backend.app.models.workforce_hr_document_verification",
        "WorkforceHrDocumentVerification",
    ),
    "WorkforceHrReview": ("backend.app.models.workforce_hr_review", "WorkforceHrReview"),
    "WorkforceHrVerifiedField": ("backend.app.models.workforce_hr_verified_field", "WorkforceHrVerifiedField"),
    "WorkforceLifecycleEvent": ("backend.app.models.workforce_lifecycle_event", "WorkforceLifecycleEvent"),
    "WorkforceStartAllowedException": (
        "backend.app.models.workforce_start_allowed_exception",
        "WorkforceStartAllowedException",
    ),
    "WorkforceWorkEligibilityPaymentRequirement": (
        "backend.app.models.workforce_work_eligibility_payment_requirement",
        "WorkforceWorkEligibilityPaymentRequirement",
    ),
}

__all__ = sorted(_SOURCE)


def __getattr__(name: str) -> Any:
    if name not in _SOURCE:
        raise AttributeError(name)
    import importlib

    mod_name, attr = _SOURCE[name]
    return getattr(importlib.import_module(mod_name), attr)


def __dir__() -> list[str]:
    return list(__all__)
