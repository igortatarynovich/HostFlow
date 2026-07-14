"""REF-1A Registry facade for system reference domains.

This module does not own domain logic. It registers:
- available domains
- source module
- reader
- validator
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final

from .catalogs import COUNTRIES, LANGUAGES
from backend.app.reference.company_setup_catalogs import (
    list_business_types,
    list_first_modules,
    list_industries,
    list_platform_identities,
    list_team_sizes,
    list_vacancy_search_categories,
)
from backend.app.reference.geo_cities_catalog import list_cities
from .operational_risk_reference import (
    COMPLIANCE_DOMAIN_CODES,
    IMPACT_CODES,
    NEXT_ACTION_CODES,
    SEVERITY_CODES,
    SEVERITY_DICTIONARY,
    SIGNAL_CODES,
    STATUS_CODES,
    validate_impact,
    validate_compliance_domain,
    validate_next_action,
    validate_severity,
    validate_signal,
    validate_status,
)

DomainReader = Callable[[], list[dict[str, Any]]]
DomainValidator = Callable[[str], str]


@dataclass(frozen=True)
class ReferenceDomainSpec:
    code: str
    source: str
    reader: DomainReader
    validator: DomainValidator | None = None


def _identity(value: str) -> str:
    return (value or "").strip()


def _countries() -> list[dict[str, Any]]:
    return [{"code": k, "name": v} for k, v in sorted(COUNTRIES.items(), key=lambda x: x[1])]


def _country_codes() -> list[dict[str, Any]]:
    return [{"code": k} for k in sorted(COUNTRIES.keys())]


def _citizenships() -> list[dict[str, Any]]:
    return [{"code": k, "label": v} for k, v in sorted(COUNTRIES.items(), key=lambda x: x[1])]


def _languages() -> list[dict[str, Any]]:
    return [{"code": k, "name": v} for k, v in sorted(LANGUAGES.items(), key=lambda x: x[1])]


def _severity_domain() -> list[dict[str, Any]]:
    return [{"code": c, **SEVERITY_DICTIONARY[c]} for c in SEVERITY_CODES]


def _codes(values: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{"code": c} for c in values]


DOMAIN_REGISTRY: Final[dict[str, ReferenceDomainSpec]] = {
    "countries": ReferenceDomainSpec("countries", "catalogs", _countries),
    "country_iso_codes": ReferenceDomainSpec("country_iso_codes", "catalogs", _country_codes),
    "citizenships": ReferenceDomainSpec("citizenships", "catalogs", _citizenships),
    "languages": ReferenceDomainSpec("languages", "catalogs", _languages),
    "risk_severities": ReferenceDomainSpec("risk_severities", "operational_risk_reference", _severity_domain, validate_severity),
    "operational_impacts": ReferenceDomainSpec("operational_impacts", "operational_risk_reference", lambda: _codes(IMPACT_CODES), validate_impact),
    "next_actions": ReferenceDomainSpec("next_actions", "operational_risk_reference", lambda: _codes(NEXT_ACTION_CODES), validate_next_action),
    "operational_statuses": ReferenceDomainSpec("operational_statuses", "operational_risk_reference", lambda: _codes(STATUS_CODES), validate_status),
    "operational_signals": ReferenceDomainSpec("operational_signals", "operational_risk_reference", lambda: _codes(SIGNAL_CODES), validate_signal),
    "compliance_domains": ReferenceDomainSpec(
        "compliance_domains",
        "operational_risk_reference",
        lambda: _codes(COMPLIANCE_DOMAIN_CODES),
        validate_compliance_domain,
    ),
    "industries": ReferenceDomainSpec("industries", "company_setup_catalogs", list_industries),
    "team_sizes": ReferenceDomainSpec(
        "team_sizes",
        "company_setup_catalogs",
        lambda: list_team_sizes(onboarding=False),
    ),
    "team_sizes_onboarding": ReferenceDomainSpec(
        "team_sizes_onboarding",
        "company_setup_catalogs",
        lambda: list_team_sizes(onboarding=True),
    ),
    "business_types": ReferenceDomainSpec("business_types", "company_setup_catalogs", list_business_types),
    "platform_identities": ReferenceDomainSpec(
        "platform_identities",
        "company_setup_catalogs",
        list_platform_identities,
    ),
    "first_modules": ReferenceDomainSpec("first_modules", "company_setup_catalogs", list_first_modules),
    "vacancy_search_categories": ReferenceDomainSpec(
        "vacancy_search_categories",
        "company_setup_catalogs",
        list_vacancy_search_categories,
    ),
    "cities": ReferenceDomainSpec("cities", "geo_cities_catalog", list_cities),
    "lifecycle_statuses": ReferenceDomainSpec(
        "lifecycle_statuses",
        "lifecycle_reference",
        lambda: _codes(("requested", "uploaded", "verification_required", "verified", "rejected", "expired", "renewal_required", "archived")),
        _identity,
    ),
    "event_codes": ReferenceDomainSpec(
        "event_codes",
        "lifecycle_reference",
        lambda: _codes(("document_reference_resolved", "document_reference_runtime_fallback_used", "workforce_action_allowed", "workforce_action_blocked")),
        _identity,
    ),
    "document_categories": ReferenceDomainSpec(
        "document_categories",
        "document_reference",
        lambda: _codes(("identity", "immigration", "work_authorization", "driver_qualification", "medical", "employment", "payroll", "tax", "social_security", "internal_hr", "fleet_compliance", "other")),
        _identity,
    ),
    "document_types": ReferenceDomainSpec(
        "document_types",
        "document_reference",
        lambda: _codes(("passport", "id_card", "residence_card", "visa", "work_permit", "driver_license", "code_95", "tachograph_card", "medical_certificate", "psychotest", "employment_contract", "civil_contract", "zus_zua", "zus_zza", "tax_declaration", "other")),
        _identity,
    ),
    "visa_types": ReferenceDomainSpec("visa_types", "document_reference", lambda: _codes(("schengen_c", "national_d", "temporary", "other")), _identity),
    "work_permit_types": ReferenceDomainSpec("work_permit_types", "document_reference", lambda: _codes(("type_a", "type_b", "type_c", "declaration", "other")), _identity),
    "residence_basis_types": ReferenceDomainSpec("residence_basis_types", "document_reference", lambda: _codes(("visa", "residence_card", "temporary_protection", "eu_citizen", "other")), _identity),
    "driver_license_categories": ReferenceDomainSpec("driver_license_categories", "transport_reference", lambda: _codes(("AM", "A1", "A2", "A", "B", "BE", "C1", "C1E", "C", "CE", "D1", "D1E", "D", "DE", "T")), _identity),
    "transport_types": ReferenceDomainSpec("transport_types", "transport_reference", lambda: _codes(("truck", "van", "bus", "car", "rail", "other")), _identity),
    "employment_types": ReferenceDomainSpec("employment_types", "employment_reference", lambda: _codes(("employment_contract", "civil_contract", "b2b", "internship", "other")), _identity),
    "vacancy_categories": ReferenceDomainSpec("vacancy_categories", "employment_reference", lambda: _codes(("driver", "warehouse", "mechanic", "dispatcher", "office", "subcontractor", "other")), _identity),
    "currencies": ReferenceDomainSpec("currencies", "country_reference", lambda: _codes(("PLN", "EUR", "USD", "CZK", "UAH", "GBP")), _identity),
}

REFERENCE_DOMAINS: Final[tuple[str, ...]] = tuple(DOMAIN_REGISTRY.keys())
RISK_SEVERITY_DICTIONARY: Final[dict[str, dict[str, Any]]] = SEVERITY_DICTIONARY


def get_reference_domain(domain: str) -> list[dict[str, Any]]:
    spec = DOMAIN_REGISTRY.get((domain or "").strip().lower())
    return spec.reader() if spec else []


def validate_reference_code(domain: str, value: str) -> str:
    spec = DOMAIN_REGISTRY.get((domain or "").strip().lower())
    if spec is None or spec.validator is None:
        return _identity(value)
    return spec.validator(value)


def validate_operational_severity(value: str) -> str:
    return validate_reference_code("risk_severities", value)
