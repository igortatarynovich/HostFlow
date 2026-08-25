"""Forms Platform C5 — Form Execution.

Runtime Model → Validation → Submission → Persistence.
Does not import Builder, publish, or re-mint Contract Identity.
Shared Intake remains the public write path — no second submit engine.
"""

from __future__ import annotations

from backend.app.forms_platform.execution.execute import (
    PUBLIC_INTAKE_PATH,
    execute_submission,
    persist_execution,
    submission_pin,
    validate_against_runtime_model,
)

__all__ = [
    "PUBLIC_INTAKE_PATH",
    "execute_submission",
    "persist_execution",
    "submission_pin",
    "validate_against_runtime_model",
]
