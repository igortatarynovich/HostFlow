"""HR review commands/queries published to Employment (not Workforce internals)."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "HR_REVIEW_STATUS_APPROVED": ("backend.app.services.workforce_hr_review", "HR_REVIEW_STATUS_APPROVED"),
    "HrReviewBlockedError": ("backend.app.services.workforce_hr_review", "HrReviewBlockedError"),
    "_recompute_review_blockers_from_checklist": (
        "backend.app.services.workforce_hr_review",
        "_recompute_review_blockers_from_checklist",
    ),
    "approve_hr_review_record": ("backend.app.services.workforce_hr_review", "approve_hr_review_record"),
    "ensure_hr_review_for_employee": (
        "backend.app.services.workforce_hr_review",
        "ensure_hr_review_for_employee",
    ),
    "ensure_hr_review_for_handoff": (
        "backend.app.services.workforce_hr_review",
        "ensure_hr_review_for_handoff",
    ),
    "finalize_hr_review_can_approve": (
        "backend.app.services.workforce_hr_review",
        "finalize_hr_review_can_approve",
    ),
    "get_hr_review_by_handoff": ("backend.app.services.workforce_hr_review", "get_hr_review_by_handoff"),
    "recompute_review_blockers_from_checklist": (
        "backend.app.services.workforce_hr_review",
        "_recompute_review_blockers_from_checklist",
    ),
}

__all__ = sorted(k for k in _SOURCE if not k.startswith("_"))


def __getattr__(name: str) -> Any:
    # Allow stable public name without leading underscore.
    key = name
    if name == "recompute_review_blockers_from_checklist":
        key = "_recompute_review_blockers_from_checklist"
    if name not in _SOURCE and key not in _SOURCE:
        raise AttributeError(name)
    import importlib

    mod_name, attr = _SOURCE[key if key in _SOURCE else name]
    return getattr(importlib.import_module(mod_name), attr)


def __dir__() -> list[str]:
    return list(__all__)
