"""Canonical facts bag for intake writes (MA-4).

Intake mapping writes ``canonical_facts_v1[qualified_code]``. Leftover flat
``target`` keys are not a second destination vocabulary.

Lead identity fields (phone / email / name) and lead-only routing hints may be
projected onto the lead row for matching and routing. That projection is
storage, not a mapping decision.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from backend.app.field_registry.intake_mapping import rule_write_qualified_code
from backend.app.field_registry.option_map import OPTION_IGNORE_VALUE, lookup_option_map

CANONICAL_FACTS_V1 = "canonical_facts_v1"

# Storage projection for matching / routing — not a mapping vocabulary.
LEAD_STORAGE_FROM_QUALIFIED: dict[str, str] = {
    "recruitment.candidate.contacts.phone": "phone",
    "recruitment.candidate.contacts.email": "email",
    "recruitment.candidate.contacts.phone_country_code": "phone_country_code",
    "recruitment.candidate.first_name": "first_name",
    "recruitment.candidate.last_name": "last_name",
    "recruitment.lead.vacancy_id": "vacancy_id",
    "recruitment.lead.vacancy_id_hint": "vacancy_hint",
    "recruitment.lead.company_id_hint": "company_id",
    "recruitment.lead.company_name_hint": "company_name_hint",
}


def canonical_facts_of(normalized: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = (normalized or {}).get(CANONICAL_FACTS_V1)
    return dict(raw) if isinstance(raw, Mapping) else {}


def write_canonical_fact(
    normalized: dict[str, Any],
    qualified: str,
    value: Any,
    *,
    overwrite: bool = True,
) -> bool:
    """Write one Mapping Authority destination. Returns True when the bag changed."""
    code = str(qualified or "").strip()
    if not code or value is None or value == "":
        return False
    facts = normalized.get(CANONICAL_FACTS_V1)
    if not isinstance(facts, dict):
        facts = {}
        normalized[CANONICAL_FACTS_V1] = facts
    if not overwrite and facts.get(code) not in (None, ""):
        return False
    facts[code] = value
    lead_key = LEAD_STORAGE_FROM_QUALIFIED.get(code)
    if lead_key and (overwrite or lead_key not in normalized or normalized.get(lead_key) in (None, "")):
        normalized[lead_key] = value
    return True


def merge_canonical_facts(
    normalized: dict[str, Any],
    facts: Mapping[str, Any] | None,
    *,
    overwrite: bool = True,
) -> None:
    if not isinstance(facts, Mapping):
        return
    for qualified, value in facts.items():
        write_canonical_fact(normalized, str(qualified), value, overwrite=overwrite)


def _source_value(sources: Mapping[str, Any], source: str) -> Any:
    if not source:
        return None
    if source in sources:
        return sources[source]
    lowered = source.lower()
    for key, value in sources.items():
        if str(key).strip().lower() == lowered:
            return value
    return None


def apply_authority_rules_to_sources(
    sources: Mapping[str, Any],
    rules: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Execute Mapping Authority rules onto a qualified facts bag."""
    facts: dict[str, Any] = {}
    for raw in rules or []:
        if not isinstance(raw, Mapping):
            continue
        if str(raw.get("action") or "").strip().lower() == "ignore":
            continue
        source = str(raw.get("source") or "").strip()
        qualified = rule_write_qualified_code(dict(raw))
        if not source or not qualified:
            continue
        value = _source_value(sources, source)
        if value is None or value == "":
            continue
        option_map = raw.get("option_map") if isinstance(raw.get("option_map"), dict) else None
        if option_map:
            looked = lookup_option_map(option_map, value)
            if looked == OPTION_IGNORE_VALUE:
                continue
            if looked is not None:
                value = looked
        facts[qualified] = value
    return facts


__all__ = [
    "CANONICAL_FACTS_V1",
    "LEAD_STORAGE_FROM_QUALIFIED",
    "apply_authority_rules_to_sources",
    "canonical_facts_of",
    "merge_canonical_facts",
    "write_canonical_fact",
]
