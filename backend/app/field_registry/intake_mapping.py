"""Lead / Meta intake field mapping bridge — qualified codes ↔ legacy normalized targets (P5)."""

from __future__ import annotations

from typing import Any

# Canonical recruitment.candidate.* / platform.identity.* → lead.normalized flat keys.
LEAD_INTAKE_QUALIFIED_TO_NORMALIZED: dict[str, str] = {
    "recruitment.candidate.first_name": "first_name",
    "recruitment.candidate.last_name": "last_name",
    "recruitment.candidate.contacts.phone": "phone",
    "recruitment.candidate.contacts.phone_country_code": "phone_country_code",
    "recruitment.candidate.contacts.email": "email",
    "recruitment.candidate.contacts.preferred_messenger": "preferred_contact",
    "platform.identity.citizenship": "country",
    "platform.identity.address": "address",
    "platform.identity.birth_date": "birth_date",
    "recruitment.candidate.personal.residency_status": "poland_stay_basis",
    "recruitment.candidate.personal.current_location": "current_location",
    "recruitment.candidate.personal.in_poland": "in_poland",
    "recruitment.candidate.experience.years_ce": "experience_eu_years",
    "recruitment.candidate.experience.intl_experience": "intl_experience",
    # Lead-normalized hints (not yet candidate columns — intake layer only).
    "recruitment.lead.vacancy_id_hint": "vacancy_hint",
    "recruitment.lead.vacancy_id": "vacancy_id",
    "recruitment.lead.company_id_hint": "company_id",
    "recruitment.lead.company_name_hint": "company_name_hint",
}

# Extend with legacy Meta preset targets that map to the same normalized keys.
_LEGACY_TARGET_ALIASES: dict[str, str] = {
    "full_name": "full_name",
    "country": "country",
    "country_raw": "country_raw",
    "geo_country": "geo_country",
    "geo_country_raw": "geo_country_raw",
    "location_country": "location_country",
    "current_country": "current_country",
    "vacancy_id_hint": "vacancy_id_hint",
    "vacancy_hint": "vacancy_hint",
    "company_id_hint": "company_id_hint",
    "driving_experience_in_europe": "driving_experience_in_europe",
    "citizenship": "citizenship",
}

QUALIFIED_BY_LEGACY_NORMALIZED: dict[str, str] = {
    v: k for k, v in LEAD_INTAKE_QUALIFIED_TO_NORMALIZED.items()
}


def legacy_normalized_target_from_qualified(qualified_code: str) -> str | None:
    code = str(qualified_code or "").strip()
    if not code:
        return None
    return LEAD_INTAKE_QUALIFIED_TO_NORMALIZED.get(code)


def qualified_code_from_legacy_target(target: str) -> str | None:
    key = str(target or "").strip()
    if not key:
        return None
    if key in QUALIFIED_BY_LEGACY_NORMALIZED:
        return QUALIFIED_BY_LEGACY_NORMALIZED[key]
    return None


def resolve_intake_mapping_target(rule: dict[str, Any]) -> str:
    """Effective normalized path for Meta/custom mapping rule (qualified code wins)."""
    qualified = str(rule.get("qualified_field_code") or "").strip()
    if qualified:
        mapped = legacy_normalized_target_from_qualified(qualified)
        if mapped:
            return mapped
        # Allow qualified codes that use dot paths directly when they match normalized nesting.
        return qualified
    target = str(rule.get("target") or "").strip()
    if not target:
        return ""
    if target in _LEGACY_TARGET_ALIASES:
        return _LEGACY_TARGET_ALIASES[target]
    return target


def enrich_mapping_rule_for_storage(rule: dict[str, Any]) -> dict[str, Any]:
    """Ensure legacy ``target`` is populated when only qualified_field_code is set."""
    out = dict(rule)
    qualified = str(out.get("qualified_field_code") or "").strip()
    target = str(out.get("target") or "").strip()
    if qualified and not target:
        legacy = legacy_normalized_target_from_qualified(qualified)
        if legacy:
            out["target"] = legacy
    elif target and not qualified:
        inferred = qualified_code_from_legacy_target(target)
        if inferred:
            out["qualified_field_code"] = inferred
    return out


def enrich_mapping_rules_for_storage(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_mapping_rule_for_storage(r) for r in rules if isinstance(r, dict)]
