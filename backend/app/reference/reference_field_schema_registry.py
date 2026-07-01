from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ReferenceFieldSchemaItem:
    field_key: str
    field_type: str
    group: str
    label: str
    description: str
    reference_domain: str


CATALOG_VERSION: Final[str] = "ref4-phase1c-field-schema-v1"


LEGAL_DOCUMENT_REFERENCE_FIELD_SCHEMAS: Final[tuple[ReferenceFieldSchemaItem, ...]] = (
    ReferenceFieldSchemaItem(
        field_key="citizenship",
        field_type="code_alpha2",
        group="legal_identity",
        label="Citizenship",
        description="Canonical citizenship code (ISO alpha-2).",
        reference_domain="citizenships",
    ),
    ReferenceFieldSchemaItem(
        field_key="legal_status",
        field_type="code",
        group="legal_identity",
        label="Legal Status",
        description="Canonical residency/legal status code.",
        reference_domain="legal_statuses",
    ),
    ReferenceFieldSchemaItem(
        field_key="permit_type",
        field_type="code",
        group="work_authorization",
        label="Permit Type",
        description="Canonical work permit type code.",
        reference_domain="permit_types",
    ),
    ReferenceFieldSchemaItem(
        field_key="visa_type",
        field_type="code",
        group="work_authorization",
        label="Visa Type",
        description="Canonical visa type code.",
        reference_domain="visa_types",
    ),
    ReferenceFieldSchemaItem(
        field_key="document_type",
        field_type="code",
        group="document_identity",
        label="Document Type",
        description="Canonical document type code.",
        reference_domain="document_types",
    ),
    ReferenceFieldSchemaItem(
        field_key="document_category",
        field_type="code",
        group="document_identity",
        label="Document Category",
        description="Canonical document category code.",
        reference_domain="document_categories",
    ),
)

WORKFORCE_TRANSPORT_REFERENCE_FIELD_SCHEMAS: Final[tuple[ReferenceFieldSchemaItem, ...]] = (
    ReferenceFieldSchemaItem(
        field_key="workforce_category",
        field_type="code",
        group="workforce_profile",
        label="Workforce Category",
        description="Canonical workforce category code.",
        reference_domain="workforce_categories",
    ),
    ReferenceFieldSchemaItem(
        field_key="employment_type",
        field_type="code",
        group="workforce_profile",
        label="Employment Type",
        description="Canonical employment type code.",
        reference_domain="employment_types",
    ),
    ReferenceFieldSchemaItem(
        field_key="transport_mode",
        field_type="code",
        group="transport_profile",
        label="Transport Mode",
        description="Canonical transport mode code.",
        reference_domain="transport_modes",
    ),
    ReferenceFieldSchemaItem(
        field_key="transport_qualification_type",
        field_type="code",
        group="transport_profile",
        label="Transport Qualification Type",
        description="Canonical transport qualification type code.",
        reference_domain="transport_qualification_types",
    ),
    ReferenceFieldSchemaItem(
        field_key="driver_capability_class",
        field_type="code",
        group="transport_profile",
        label="Driver Capability Class",
        description="Canonical driver capability class code.",
        reference_domain="driver_capability_classes",
    ),
)


FIELDS_BY_KEY: Final[dict[str, ReferenceFieldSchemaItem]] = {
    item.field_key: item
    for item in (*LEGAL_DOCUMENT_REFERENCE_FIELD_SCHEMAS, *WORKFORCE_TRANSPORT_REFERENCE_FIELD_SCHEMAS)
}


def list_reference_field_schemas() -> tuple[ReferenceFieldSchemaItem, ...]:
    return (*LEGAL_DOCUMENT_REFERENCE_FIELD_SCHEMAS, *WORKFORCE_TRANSPORT_REFERENCE_FIELD_SCHEMAS)


def get_reference_field_schema(field_key: str | None) -> ReferenceFieldSchemaItem | None:
    if field_key is None:
        return None
    normalized = str(field_key).strip().lower()
    if not normalized:
        return None
    return FIELDS_BY_KEY.get(normalized)


def _assert_unique_field_keys() -> None:
    keys = [item.field_key for item in list_reference_field_schemas()]
    assert len(keys) == len(set(keys)), "Duplicate field key in reference field schema registry"


_assert_unique_field_keys()


__all__ = [
    "CATALOG_VERSION",
    "ReferenceFieldSchemaItem",
    "LEGAL_DOCUMENT_REFERENCE_FIELD_SCHEMAS",
    "WORKFORCE_TRANSPORT_REFERENCE_FIELD_SCHEMAS",
    "list_reference_field_schemas",
    "get_reference_field_schema",
]
