"""Handoff query/command helpers published to spine neighbours.

Lazy re-exports avoid import cycles with Recruitment/Employment public packages.
"""

from __future__ import annotations

from typing import Any, Callable

_EXPORTS = {
    "can_agency_edit",
    "can_client_edit",
    "client_has_accepted_handoff",
    "ensure_internal_hr_handoff_checklist_activities",
    "get_accepted_handoff",
    "get_accepted_handoff_for_agency",
    "get_pending_handoff",
    "get_pending_handoff_for_agency",
    "has_pending_handoff_for_client",
    "is_client_tenant",
    "is_client_tenant_for_list",
    "return_handoff",
    "unlock_pending_handoff_for_recruitment_close",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Callable[..., Any]:
    if name not in _EXPORTS:
        raise AttributeError(name)
    from backend.app.services import handoff as _impl

    if name == "ensure_internal_hr_handoff_checklist_activities":
        return getattr(_impl, "_ensure_internal_hr_handoff_checklist_activities")
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return list(__all__)
