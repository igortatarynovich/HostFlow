"""Canonical activity types for the internal-HR operational lane.

Used by HR inbox, HR dashboard aggregates, ``GET /api/v1/hr/tasks``, and
``handoff`` materialization so filters and writes never drift apart.
"""

from __future__ import annotations

INTERNAL_HR_HANDOFF_PENDING = "internal_hr_handoff_pending"
HANDOFF_HR_CHECKLIST = "handoff_hr_checklist"

HR_TASK_TYPES: tuple[str, ...] = (
    INTERNAL_HR_HANDOFF_PENDING,
    HANDOFF_HR_CHECKLIST,
)

__all__ = [
    "HANDOFF_HR_CHECKLIST",
    "HR_TASK_TYPES",
    "INTERNAL_HR_HANDOFF_PENDING",
]
