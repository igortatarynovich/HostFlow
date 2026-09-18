"""Employment-owned HR employee funnel type constants.

Shared with Recruitment only via process contracts — not via
``backend.app.constants.funnel_types`` imports from Employment runtime.
"""

from __future__ import annotations

HR_MODULE_KEY = "hr"
HR_EMPLOYEE_FUNNEL_TYPE = "employee"
PLATFORM_SEED_TENANT_ID = "default"


def is_hr_employee_funnel_type(funnel_type: str) -> bool:
    return str(funnel_type or "").strip() == HR_EMPLOYEE_FUNNEL_TYPE


__all__ = [
    "HR_EMPLOYEE_FUNNEL_TYPE",
    "HR_MODULE_KEY",
    "PLATFORM_SEED_TENANT_ID",
    "is_hr_employee_funnel_type",
]
