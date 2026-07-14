"""Citizenship segmentation for Requirement Policy (ADR-018 PR 2A.1)."""

from __future__ import annotations

from typing import Optional

from backend.app.requirement_rules.requirement_rule_contract import CitizenshipSegment

# EU member states + EEA + Switzerland (free movement to Poland for work).
EU_EEA_SWISS_CODES = frozenset(
    {
        "at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie",
        "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se",
        "is", "li", "no", "ch",
    }
)


def normalize_country_code(value: Optional[str]) -> str:
    return str(value or "").strip().lower()


def citizenship_segment(citizenship: Optional[str]) -> CitizenshipSegment:
    code = normalize_country_code(citizenship)
    if not code:
        return CitizenshipSegment.unknown
    if code == "pl":
        return CitizenshipSegment.poland
    if code in EU_EEA_SWISS_CODES:
        return CitizenshipSegment.eu_eea_swiss
    return CitizenshipSegment.third_country


def is_free_movement_citizen(citizenship: Optional[str]) -> bool:
    seg = citizenship_segment(citizenship)
    return seg in {CitizenshipSegment.poland, CitizenshipSegment.eu_eea_swiss}


__all__ = [
    "EU_EEA_SWISS_CODES",
    "citizenship_segment",
    "is_free_movement_citizen",
    "normalize_country_code",
]
