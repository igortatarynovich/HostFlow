"""Boundary-facing Employment process commands (handoff cutover surface).

Closes EXC-PMI-B-EMP: Boundary must not import Employment orchestrator modules.
``employment_start_allowed`` rulesets remain internal — only handoff host
evaluate/apply are published. ESO-5 internals are not published; only
``confirm_employment_started_for_handoff`` (started.v1 entry).
"""

from __future__ import annotations

from backend.app.services.employment_accept_orchestrator import (
    EmploymentAcceptError,
    apply_employment_accept_after_transfer,
    apply_employment_accept_policy,
)
from backend.app.services.employment_formalize_orchestrator import (
    EmploymentFormalizeError,
    formalize_employment_for_handoff,
    formalize_request_is_authoritative_apply,
)
from backend.app.services.employment_missing_resolution_orchestrator import (
    EmploymentMissingResolutionError,
    resolve_employment_missing_for_handoff,
)
from backend.app.services.employment_start_allowed_orchestrator import (
    EmploymentStartAllowedHostError,
    apply_start_allowed_for_handoff,
    evaluate_start_allowed_for_handoff,
)
from backend.app.services.employment_started_orchestrator import (
    EmploymentStartedError,
    confirm_employment_started_for_handoff,
)
from backend.app.services.hr_acceptance_orchestrator import (
    accept_internal_hr_handoff,
    approve_employment_for_handoff,
)

__all__ = [
    "EmploymentAcceptError",
    "EmploymentFormalizeError",
    "EmploymentMissingResolutionError",
    "EmploymentStartAllowedHostError",
    "EmploymentStartedError",
    "accept_internal_hr_handoff",
    "apply_employment_accept_after_transfer",
    "apply_employment_accept_policy",
    "apply_start_allowed_for_handoff",
    "approve_employment_for_handoff",
    "confirm_employment_started_for_handoff",
    "evaluate_start_allowed_for_handoff",
    "formalize_employment_for_handoff",
    "formalize_request_is_authoritative_apply",
    "resolve_employment_missing_for_handoff",
]
