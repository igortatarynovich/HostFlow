from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CitizenshipCatalogItem:
    code_alpha2: str
    label: str


@dataclass(frozen=True)
class LegalStatusCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class PermitTypeCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class VisaTypeCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class DocumentCategoryCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class DocumentTypeCatalogItem:
    code: str
    label: str
    category_code: str
    expiry_track_required: bool = False


CATALOG_VERSION: Final[str] = "ref4-phase1b-legal-document-v1"


CITIZENSHIPS_CANONICAL: Final[tuple[CitizenshipCatalogItem, ...]] = (
    CitizenshipCatalogItem("PL", "Polish"),
    CitizenshipCatalogItem("DE", "German"),
    CitizenshipCatalogItem("UA", "Ukrainian"),
)

LEGAL_STATUSES_CANONICAL: Final[tuple[LegalStatusCatalogItem, ...]] = (
    LegalStatusCatalogItem("eu_citizen", "EU Citizen"),
    LegalStatusCatalogItem("temporary_resident", "Temporary Resident"),
    LegalStatusCatalogItem("permanent_resident", "Permanent Resident"),
)

PERMIT_TYPES_CANONICAL: Final[tuple[PermitTypeCatalogItem, ...]] = (
    PermitTypeCatalogItem("type_a", "Type A"),
    PermitTypeCatalogItem("type_b", "Type B"),
    PermitTypeCatalogItem("declaration", "Employer Declaration"),
)

VISA_TYPES_CANONICAL: Final[tuple[VisaTypeCatalogItem, ...]] = (
    VisaTypeCatalogItem("schengen_c", "Schengen C"),
    VisaTypeCatalogItem("national_d", "National D"),
    VisaTypeCatalogItem("temporary", "Temporary"),
)

DOCUMENT_CATEGORIES_CANONICAL: Final[tuple[DocumentCategoryCatalogItem, ...]] = (
    DocumentCategoryCatalogItem("identity", "Identity"),
    DocumentCategoryCatalogItem("immigration", "Immigration"),
    DocumentCategoryCatalogItem("work_authorization", "Work Authorization"),
)

DOCUMENT_TYPES_CANONICAL: Final[tuple[DocumentTypeCatalogItem, ...]] = (
    DocumentTypeCatalogItem("passport", "Passport", "identity", expiry_track_required=True),
    DocumentTypeCatalogItem("id_card", "ID Card", "identity", expiry_track_required=True),
    DocumentTypeCatalogItem("residence_card", "Residence Card", "immigration", expiry_track_required=True),
    DocumentTypeCatalogItem("visa", "Visa", "immigration", expiry_track_required=True),
    DocumentTypeCatalogItem("work_permit", "Work Permit", "work_authorization", expiry_track_required=True),
)


def _normalize_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _normalize_alpha2(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


DOCUMENT_TYPES_BY_CODE: Final[dict[str, DocumentTypeCatalogItem]] = {
    item.code: item for item in DOCUMENT_TYPES_CANONICAL
}
DOCUMENT_CATEGORIES_BY_CODE: Final[dict[str, DocumentCategoryCatalogItem]] = {
    item.code: item for item in DOCUMENT_CATEGORIES_CANONICAL
}
LEGAL_STATUSES_BY_CODE: Final[dict[str, LegalStatusCatalogItem]] = {
    item.code: item for item in LEGAL_STATUSES_CANONICAL
}
PERMIT_TYPES_BY_CODE: Final[dict[str, PermitTypeCatalogItem]] = {
    item.code: item for item in PERMIT_TYPES_CANONICAL
}
VISA_TYPES_BY_CODE: Final[dict[str, VisaTypeCatalogItem]] = {
    item.code: item for item in VISA_TYPES_CANONICAL
}
CITIZENSHIPS_BY_ALPHA2: Final[dict[str, CitizenshipCatalogItem]] = {
    item.code_alpha2: item for item in CITIZENSHIPS_CANONICAL
}


def list_citizenships_canonical() -> tuple[CitizenshipCatalogItem, ...]:
    return CITIZENSHIPS_CANONICAL


def list_legal_statuses_canonical() -> tuple[LegalStatusCatalogItem, ...]:
    return LEGAL_STATUSES_CANONICAL


def list_permit_types_canonical() -> tuple[PermitTypeCatalogItem, ...]:
    return PERMIT_TYPES_CANONICAL


def list_visa_types_canonical() -> tuple[VisaTypeCatalogItem, ...]:
    return VISA_TYPES_CANONICAL


def list_document_categories_canonical() -> tuple[DocumentCategoryCatalogItem, ...]:
    return DOCUMENT_CATEGORIES_CANONICAL


def list_document_types_canonical() -> tuple[DocumentTypeCatalogItem, ...]:
    return DOCUMENT_TYPES_CANONICAL


def get_document_type_by_code(code: str | None) -> DocumentTypeCatalogItem | None:
    normalized = _normalize_code(code)
    if normalized is None:
        return None
    return DOCUMENT_TYPES_BY_CODE.get(normalized)


def get_citizenship_by_alpha2(code: str | None) -> CitizenshipCatalogItem | None:
    normalized = _normalize_alpha2(code)
    if normalized is None:
        return None
    return CITIZENSHIPS_BY_ALPHA2.get(normalized)


def _assert_unique_codes() -> None:
    citizenships = [item.code_alpha2 for item in CITIZENSHIPS_CANONICAL]
    legal_statuses = [item.code for item in LEGAL_STATUSES_CANONICAL]
    permit_types = [item.code for item in PERMIT_TYPES_CANONICAL]
    visa_types = [item.code for item in VISA_TYPES_CANONICAL]
    categories = [item.code for item in DOCUMENT_CATEGORIES_CANONICAL]
    doc_types = [item.code for item in DOCUMENT_TYPES_CANONICAL]
    assert len(citizenships) == len(set(citizenships)), "Duplicate citizenship alpha2 code"
    assert len(legal_statuses) == len(set(legal_statuses)), "Duplicate legal status code"
    assert len(permit_types) == len(set(permit_types)), "Duplicate permit type code"
    assert len(visa_types) == len(set(visa_types)), "Duplicate visa type code"
    assert len(categories) == len(set(categories)), "Duplicate document category code"
    assert len(doc_types) == len(set(doc_types)), "Duplicate document type code"


_assert_unique_codes()


__all__ = [
    "CATALOG_VERSION",
    "CitizenshipCatalogItem",
    "LegalStatusCatalogItem",
    "PermitTypeCatalogItem",
    "VisaTypeCatalogItem",
    "DocumentCategoryCatalogItem",
    "DocumentTypeCatalogItem",
    "CITIZENSHIPS_CANONICAL",
    "LEGAL_STATUSES_CANONICAL",
    "PERMIT_TYPES_CANONICAL",
    "VISA_TYPES_CANONICAL",
    "DOCUMENT_CATEGORIES_CANONICAL",
    "DOCUMENT_TYPES_CANONICAL",
    "list_citizenships_canonical",
    "list_legal_statuses_canonical",
    "list_permit_types_canonical",
    "list_visa_types_canonical",
    "list_document_categories_canonical",
    "list_document_types_canonical",
    "get_document_type_by_code",
    "get_citizenship_by_alpha2",
]
