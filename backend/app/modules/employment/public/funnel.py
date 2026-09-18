"""HR employee funnel assignment — Employment public (closes EXC-PMI-R-FUNNEL consumers)."""

from __future__ import annotations

from backend.app.services.hr_employee_funnel_assignment import (
    assign_hr_employee_pipeline_on_create,
    merge_recruitment_handoff_pipeline_meta,
)

__all__ = [
    "assign_hr_employee_pipeline_on_create",
    "merge_recruitment_handoff_pipeline_meta",
]
