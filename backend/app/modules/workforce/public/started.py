"""Started Employee intake — Workforce side of the Employment→Workforce cut.

Employment publishes ``confirm_employment_started_for_handoff`` /
``employment_started.v1``. Workforce exposes employee continuity helpers
here so Employment (and Boundary) never import Workforce ORM/services
directly when linking post-start identity.

Does **not** re-evaluate Ready, RFE, Admit, or Documents evidence.
"""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "ensure_hr_profiles_bundle": (
        "backend.app.services.workforce_employees",
        "ensure_hr_profiles_bundle",
    ),
    "find_employee_by_candidate": (
        "backend.app.services.workforce_employees",
        "find_employee_by_candidate",
    ),
    "get_work_eligibility_profile": (
        "backend.app.services.workforce_employees",
        "get_work_eligibility_profile",
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
