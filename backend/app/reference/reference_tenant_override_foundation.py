from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class TenantOverrideType:
    code: str
    label: str


@dataclass(frozen=True)
class TenantOverrideDomain:
    code: str
    label: str


@dataclass(frozen=True)
class TenantOverrideRule:
    domain_code: str
    override_type_code: str
    allowed: bool
    immutable_reason: str


CATALOG_VERSION: Final[str] = "ref4-phase1c-tenant-override-foundation-v1"


OVERRIDE_TYPES_CANONICAL: Final[tuple[TenantOverrideType, ...]] = (
    TenantOverrideType("label_override", "Label Override"),
    TenantOverrideType("visibility_override", "Visibility Override"),
)

ALLOWED_OVERRIDE_DOMAINS_CANONICAL: Final[tuple[TenantOverrideDomain, ...]] = (
    TenantOverrideDomain("citizenships", "Citizenships"),
    TenantOverrideDomain("legal_statuses", "Legal Statuses"),
    TenantOverrideDomain("permit_types", "Permit Types"),
    TenantOverrideDomain("visa_types", "Visa Types"),
    TenantOverrideDomain("document_types", "Document Types"),
    TenantOverrideDomain("document_categories", "Document Categories"),
    TenantOverrideDomain("workforce_categories", "Workforce Categories"),
    TenantOverrideDomain("employment_types", "Employment Types"),
    TenantOverrideDomain("transport_modes", "Transport Modes"),
    TenantOverrideDomain("transport_qualification_types", "Transport Qualification Types"),
    TenantOverrideDomain("driver_capability_classes", "Driver Capability Classes"),
)

IMMUTABLE_OVERRIDE_RULES_CANONICAL: Final[tuple[TenantOverrideRule, ...]] = (
    TenantOverrideRule("citizenships", "label_override", True, "Tenant can localize labels."),
    TenantOverrideRule("citizenships", "visibility_override", False, "Canonical identity domains stay globally visible."),
    TenantOverrideRule("document_types", "label_override", True, "Tenant can localize document labels."),
    TenantOverrideRule("document_types", "visibility_override", True, "Tenant can hide optional display entries."),
    TenantOverrideRule("workforce_categories", "label_override", True, "Tenant can localize workforce labels."),
    TenantOverrideRule("workforce_categories", "visibility_override", True, "Tenant can hide non-used categories."),
    TenantOverrideRule("driver_capability_classes", "label_override", False, "Regulatory class labels remain canonical."),
    TenantOverrideRule("driver_capability_classes", "visibility_override", False, "Regulatory class list remains canonical."),
)


TENANT_OVERLAY_SCHEMA_CONTRACT: Final[dict[str, str]] = {
    "tenant_id": "uuid",
    "domain": "string",
    "override_type": "string",
    "target_code": "string",
    "value": "string",
}


def list_tenant_override_types() -> tuple[TenantOverrideType, ...]:
    return OVERRIDE_TYPES_CANONICAL


def list_tenant_override_domains() -> tuple[TenantOverrideDomain, ...]:
    return ALLOWED_OVERRIDE_DOMAINS_CANONICAL


def list_tenant_override_rules() -> tuple[TenantOverrideRule, ...]:
    return IMMUTABLE_OVERRIDE_RULES_CANONICAL


def is_tenant_override_allowed(*, domain: str, override_type: str) -> bool:
    normalized_domain = str(domain or "").strip().lower()
    normalized_type = str(override_type or "").strip().lower()
    for row in IMMUTABLE_OVERRIDE_RULES_CANONICAL:
        if row.domain_code == normalized_domain and row.override_type_code == normalized_type:
            return bool(row.allowed)
    return False


def _assert_unique_codes() -> None:
    type_codes = [item.code for item in OVERRIDE_TYPES_CANONICAL]
    domain_codes = [item.code for item in ALLOWED_OVERRIDE_DOMAINS_CANONICAL]
    assert len(type_codes) == len(set(type_codes)), "Duplicate tenant override type code"
    assert len(domain_codes) == len(set(domain_codes)), "Duplicate tenant override domain code"


_assert_unique_codes()


__all__ = [
    "CATALOG_VERSION",
    "TenantOverrideType",
    "TenantOverrideDomain",
    "TenantOverrideRule",
    "TENANT_OVERLAY_SCHEMA_CONTRACT",
    "OVERRIDE_TYPES_CANONICAL",
    "ALLOWED_OVERRIDE_DOMAINS_CANONICAL",
    "IMMUTABLE_OVERRIDE_RULES_CANONICAL",
    "list_tenant_override_types",
    "list_tenant_override_domains",
    "list_tenant_override_rules",
    "is_tenant_override_allowed",
]
