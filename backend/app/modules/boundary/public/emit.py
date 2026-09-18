"""Emit-side Boundary helpers used by Recruitment when targeting HR lane."""

from __future__ import annotations

from backend.app.services.ready_for_employment_emit import (
    vacancy_is_handoff_target_for_hr_lane,
)

__all__ = [
    "vacancy_is_handoff_target_for_hr_lane",
]
