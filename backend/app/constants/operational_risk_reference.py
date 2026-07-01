"""REF-1.1 Operational risk reference dictionary (canonical domain module)."""

from __future__ import annotations

from typing import Any, Final

# Canonical code sets
SEVERITY_CODES: Final[tuple[str, ...]] = ("critical", "high", "medium", "low", "info")
IMPACT_CODES: Final[tuple[str, ...]] = (
    "legal_blocker",
    "dispatch_blocker",
    "onboarding_delay",
    "compliance_risk",
    "payroll_risk",
    "document_missing",
    "verification_pending",
)
NEXT_ACTION_CODES: Final[tuple[str, ...]] = (
    "upload_document",
    "verify_document",
    "renew_document",
    "contact_employee",
    "request_signature",
    "assign_manager",
    "escalate",
    "archive_case",
)
STATUS_CODES: Final[tuple[str, ...]] = ("blocked", "at_risk", "warning", "compliant", "pending_review")
SIGNAL_CODES: Final[tuple[str, ...]] = (
    "critical_blockers",
    "missing_required",
    "expiring_7d",
    "expiring_30d",
    "verification_needed",
    "ready_employees",
)
COMPLIANCE_DOMAIN_CODES: Final[tuple[str, ...]] = (
    "legal_stay",
    "right_to_work",
    "identity",
    "driver_compliance",
    "medical",
    "hr_onboarding",
    "payroll",
    "client_specific",
    "operational",
)

# Canonical metadata (used by UI/runtime/automation)
SEVERITY_DICTIONARY: Final[dict[str, dict[str, Any]]] = {
    "critical": {"sla_hours": 4, "blocking": True, "escalation_policy": "immediate"},
    "high": {"sla_hours": 24, "blocking": True, "escalation_policy": "urgent"},
    "medium": {"sla_hours": 48, "blocking": False, "escalation_policy": "normal"},
    "low": {"sla_hours": 120, "blocking": False, "escalation_policy": "normal"},
    "info": {"sla_hours": 168, "blocking": False, "escalation_policy": "none"},
}


def validate_severity(code: str) -> str:
    v = (code or "").strip().lower()
    return v if v in SEVERITY_CODES else "info"


def validate_impact(code: str) -> str:
    v = (code or "").strip().lower()
    return v if v in IMPACT_CODES else "compliance_risk"


def validate_next_action(code: str) -> str:
    v = (code or "").strip().lower()
    return v if v in NEXT_ACTION_CODES else "verify_document"


def validate_status(code: str) -> str:
    v = (code or "").strip().lower()
    return v if v in STATUS_CODES else "warning"


def validate_signal(code: str) -> str:
    v = (code or "").strip().lower()
    return v if v in SIGNAL_CODES else "verification_needed"


def validate_compliance_domain(code: str) -> str:
    v = (code or "").strip().lower()
    return v if v in COMPLIANCE_DOMAIN_CODES else "operational"
