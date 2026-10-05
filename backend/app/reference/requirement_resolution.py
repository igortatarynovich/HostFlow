"""Shared readings of ``requirement_resolution.v1``.

The issuing country selects the evidence shape. It does not decide that CE or
Code 95 applies, and it does not author the required document set.
"""

from __future__ import annotations

from backend.app.reference.legal_eligibility_chain import citizenship_class

POLICY_ID = "requirement_resolution.v1"

REQUIREMENT_LEVELS = frozenset({"REQUIRED", "PREFERRED", "NOT_REQUIRED"})


def issuing_evidence_shape(country: str | None) -> str | None:
    """Shared for an EU/EEA/CH licence, separate otherwise. Unknown stays unknown."""

    klass = citizenship_class(country)
    if klass is None:
        return None
    if klass in {"pl", "eu_eea_ch"}:
        return "shared"
    return "separate"
