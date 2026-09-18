"""Recruitment write-lock / handoff lane — public contract.

Exposes only the stable API. Private lock status tuples are published as
``LOCK_HANDOFF_STATUSES`` (not ``_LOCK_*`` internals).
"""

from __future__ import annotations

from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    agency_candidate_has_internal_hr_handoff_lane,
    agency_recruitment_lock_bulk_error,
    can_override_recruitment_handoff_lock,
    is_recruitment_recruiter_write_locked_by_handoff,
    require_agency_recruitment_write_allowed,
)
from backend.app.services.recruitment_handoff_write_guard import (
    _LOCK_HANDOFF_STATUSES as LOCK_HANDOFF_STATUSES,
)

__all__ = [
    "LOCK_HANDOFF_STATUSES",
    "RECRUITMENT_LOCK_OVERRIDE_ROLES",
    "agency_candidate_has_internal_hr_handoff_lane",
    "agency_recruitment_lock_bulk_error",
    "can_override_recruitment_handoff_lock",
    "is_recruitment_recruiter_write_locked_by_handoff",
    "require_agency_recruitment_write_allowed",
]
