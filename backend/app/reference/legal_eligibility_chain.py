"""Closed vocabulary of ``legal_eligibility.v1``.

Recruitment and HR read these values. A screen does not publish a second list.
Citizenship class is computed from the country registry: Poland, then a country
that is an EU member or a Schengen member (the registry's non-EU Schengen
members are Iceland, Liechtenstein, Norway, and Switzerland), then everyone else.
"""

from __future__ import annotations

from backend.app.reference.country_registry import (
    get_country_registry_entry,
    list_country_registry_entries,
)

POLICY_ID = "legal_eligibility.v1"

CITIZENSHIP_CLASS = ("pl", "eu_eea_ch", "third_country")

STAY_BASIS = (
    "not_required",
    "visa_d",
    "visa_c",
    "karta_pobytu",
    "visa_free",
    "waiting_for_trc",
    "special_protection",
    "other",
    "none",
)

# ``not_required`` is determined by the class. The operator does not pick it.
OPERATOR_STAY_CHOICES = tuple(code for code in STAY_BASIS if code != "not_required")

STAY_WITH_VISA_PARAMETERS = ("visa_d", "visa_c")

WORK_AUTHORIZATION_BASIS = ("not_required", "included_in_stay", "separate_required")

VALID_FOR_THIS_EMPLOYMENT = ("yes", "no", "operator_verification")

# Operator labels project onto a basis and, for a separate permit, a procedure type.
WORK_LABELS = {
    "work_permit": ("separate_required", "work_permit_a"),
    "oswiadczenie": ("separate_required", "employer_declaration"),
    "included_in_stay": ("included_in_stay", None),
    "not_required": ("not_required", None),
}

PROCEDURE_LABELS = frozenset({"work_permit", "oswiadczenie"})

OPERATOR_WORK_CHOICES = (
    "work_permit",
    "oswiadczenie",
    "included_in_stay",
    "not_required",
    "no_right",
)


def eu_eea_ch_alpha2() -> frozenset[str]:
    """EU members plus the non-EU Schengen members named by the country registry."""

    return frozenset(
        entry.identity.alpha2
        for entry in list_country_registry_entries()
        if entry.classifications.eu_member or entry.classifications.schengen_member
    )


def is_eu_eea_ch_country(alpha2: str | None) -> bool:
    entry = get_country_registry_entry(alpha2)
    if entry is None:
        return False
    return bool(entry.classifications.eu_member or entry.classifications.schengen_member)


def citizenship_class(citizenship: str | None) -> str | None:
    """``pl``, ``eu_eea_ch``, or ``third_country``. Absent citizenship is not a class."""

    if citizenship is None:
        return None
    code = str(citizenship).strip().upper()
    if not code:
        return None
    entry = get_country_registry_entry(code)
    if entry is None:
        return None
    if entry.identity.alpha2 == "PL":
        return "pl"
    if is_eu_eea_ch_country(entry.identity.alpha2):
        return "eu_eea_ch"
    return "third_country"
