"""Operational context / eligibility / identity / ZUS hooks for neighbours."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "WorkforceEligibilityContext": (
        "backend.app.services.workforce_eligibility_delivery_contract",
        "WorkforceEligibilityContext",
    ),
    "apply_trusted_identity_merge_variables": (
        "backend.app.services.workforce_downstream_identity",
        "apply_trusted_identity_merge_variables",
    ),
    "build_work_eligibility_journey": (
        "backend.app.services.workforce_work_eligibility_journey",
        "build_work_eligibility_journey",
    ),
    "ensure_hr_document_links": (
        "backend.app.services.workforce_hr_operational_context",
        "ensure_hr_document_links",
    ),
    "ensure_hr_operational_context": (
        "backend.app.services.workforce_hr_operational_context",
        "ensure_hr_operational_context",
    ),
    "evaluate_contract_merge_identity": (
        "backend.app.services.workforce_downstream_identity",
        "evaluate_contract_merge_identity",
    ),
    "resolve_workforce_eligibility_via_contract": (
        "backend.app.services.workforce_eligibility_delivery_contract",
        "resolve_workforce_eligibility_via_contract",
    ),
    "sync_auto_tasks_after_employee_created": (
        "backend.app.services.workforce_zus_task_autocreate",
        "sync_auto_tasks_after_employee_created",
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
