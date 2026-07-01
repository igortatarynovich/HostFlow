"""Shared funnel type constants (Recruitment + HR employee pipeline)."""

from __future__ import annotations

import re

PLATFORM_SEED_TENANT_ID = "default"

RECRUITMENT_MODULE_KEY = "recruitment"
HR_MODULE_KEY = "hr"

RECRUITMENT_FUNNEL_TYPES = frozenset({"candidate", "lead", "deal"})
HR_EMPLOYEE_FUNNEL_TYPE = "employee"
ALL_OPERATIONAL_FUNNEL_TYPES = RECRUITMENT_FUNNEL_TYPES | {HR_EMPLOYEE_FUNNEL_TYPE}

FUNNEL_TYPE_PATTERN = r"^(candidate|lead|deal|employee)$"
FUNNEL_TYPE_REGEX = re.compile(FUNNEL_TYPE_PATTERN)


def is_recruitment_funnel_type(funnel_type: str) -> bool:
    return str(funnel_type or "").strip() in RECRUITMENT_FUNNEL_TYPES


def is_hr_employee_funnel_type(funnel_type: str) -> bool:
    return str(funnel_type or "").strip() == HR_EMPLOYEE_FUNNEL_TYPE


def module_key_for_funnel_type(funnel_type: str) -> str | None:
    """Return expected module_key for an operational funnel type, or None if unknown."""
    normalized = str(funnel_type or "").strip()
    if normalized in RECRUITMENT_FUNNEL_TYPES:
        return RECRUITMENT_MODULE_KEY
    if normalized == HR_EMPLOYEE_FUNNEL_TYPE:
        return HR_MODULE_KEY
    return None


def validate_funnel_type(value: str) -> str:
    normalized = str(value or "").strip()
    if not FUNNEL_TYPE_REGEX.fullmatch(normalized):
        raise ValueError(
            f"invalid funnel type {value!r}; expected one of {sorted(ALL_OPERATIONAL_FUNNEL_TYPES)}"
        )
    return normalized
