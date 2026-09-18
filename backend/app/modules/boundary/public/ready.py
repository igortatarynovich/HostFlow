"""Ready for Employment package contract (Boundary accept/emit surface).

Employment may validate/consume packages through this module only.
Recruitment Ready composition stays in Recruitment; this is the handoff
package shape after Transfer — not Admit, not start_allowed.
"""

from __future__ import annotations

from backend.app.reference.ready_for_employment import (
    ACCEPTANCE_GATE_IDS,
    CONTRACT_ID,
    FORBIDDEN_TOP_LEVEL_KEYS,
    TRANSFER_OPERATOR_ACTION,
    is_ready_for_employment_manifest,
    is_valid_ready_for_employment_package_v1,
    validate_ready_for_employment_package_v1,
)

__all__ = [
    "ACCEPTANCE_GATE_IDS",
    "CONTRACT_ID",
    "FORBIDDEN_TOP_LEVEL_KEYS",
    "TRANSFER_OPERATOR_ACTION",
    "is_ready_for_employment_manifest",
    "is_valid_ready_for_employment_package_v1",
    "validate_ready_for_employment_package_v1",
]
