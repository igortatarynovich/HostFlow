"""Accepted evidence for the legal-eligibility chain.

A stay or work fact names a requirement and one accepted variant. It does
not name a required-set row. Document codes are registry codes. ``visa_d``
stays a stay fact; the visa document type is evidence for that fact.
``oswiadczenie`` is the registry alias of ``work_permit``, so the declaration
variant uses that code and is not a second document type.
"""

from __future__ import annotations

from typing import Any

STAY_REQUIREMENT = "legal_stay_confirmation"
WORK_REQUIREMENT = "labor_market_access"

_VISA = {
    "outcome": "needs_evidence",
    "variant": "visa",
    "document_codes": ("visa",),
}
_CARD_AND_DECISION = {
    "outcome": "needs_evidence",
    "variant": "residence_card_and_decision",
    "document_codes": ("residence_card", "temporary_residence_decision"),
}
_BLOCKING = {"outcome": "blocking", "variant": None, "document_codes": ()}
_MISSING = {"outcome": "needs_input", "variant": None, "document_codes": ()}
_NOT_REQUIRED = {"outcome": "not_required", "variant": None, "document_codes": ()}

_STAY = {
    "visa_d": _VISA,
    "visa_c": _VISA,
    "karta_pobytu": _CARD_AND_DECISION,
    "none": _BLOCKING,
    "not_required": _NOT_REQUIRED,
}

_WORK_PROCEDURE = {
    "work_permit_a": {
        "outcome": "needs_evidence",
        "variant": "work_permit_a",
        "document_codes": ("work_permit",),
    },
    "employer_declaration": {
        "outcome": "needs_evidence",
        "variant": "employer_declaration",
        "document_codes": ("work_permit",),
    },
}


def stay_accepted_evidence(stay_basis: str | None) -> dict[str, Any]:
    """The stay requirement's variant. An unlisted basis asks for no document."""

    if stay_basis is None or not str(stay_basis).strip():
        return dict(_MISSING)
    spec = _STAY.get(str(stay_basis).strip())
    if spec is None:
        return {"outcome": "needs_input", "variant": None, "document_codes": ()}
    return {
        "outcome": spec["outcome"],
        "variant": spec["variant"],
        "document_codes": tuple(spec["document_codes"]),
    }


def work_accepted_evidence(
    *,
    work_authorization_basis: str | None,
    procedure_type: str | None,
    valid_for_this_employment: str | None,
) -> dict[str, Any]:
    """The work requirement's variant for this Employment. No document list is implied by the basis alone."""

    if valid_for_this_employment == "no":
        return dict(_BLOCKING)
    basis = str(work_authorization_basis or "").strip()
    if not basis:
        return dict(_MISSING)
    if basis in {"included_in_stay", "not_required"}:
        return dict(_NOT_REQUIRED)
    if basis != "separate_required":
        return dict(_MISSING)
    spec = _WORK_PROCEDURE.get(str(procedure_type or "").strip())
    if spec is None:
        return dict(_MISSING)
    return {
        "outcome": spec["outcome"],
        "variant": spec["variant"],
        "document_codes": tuple(spec["document_codes"]),
    }
