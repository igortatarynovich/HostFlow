from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class WorkforceCategoryCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class EmploymentTypeCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class TransportModeCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class TransportQualificationTypeCatalogItem:
    code: str
    label: str


@dataclass(frozen=True)
class DriverCapabilityClassCatalogItem:
    code: str
    label: str


CATALOG_VERSION: Final[str] = "ref4-phase1c-workforce-transport-v1"


WORKFORCE_CATEGORIES_CANONICAL: Final[tuple[WorkforceCategoryCatalogItem, ...]] = (
    WorkforceCategoryCatalogItem("driver_long_haul", "Driver Long Haul"),
    WorkforceCategoryCatalogItem("driver_local", "Driver Local"),
    WorkforceCategoryCatalogItem("warehouse_operator", "Warehouse Operator"),
    WorkforceCategoryCatalogItem("dispatcher", "Dispatcher"),
)

EMPLOYMENT_TYPES_CANONICAL: Final[tuple[EmploymentTypeCatalogItem, ...]] = (
    EmploymentTypeCatalogItem("employment_contract", "Employment Contract"),
    EmploymentTypeCatalogItem("civil_contract", "Civil Contract"),
    EmploymentTypeCatalogItem("b2b", "B2B"),
)

TRANSPORT_MODES_CANONICAL: Final[tuple[TransportModeCatalogItem, ...]] = (
    TransportModeCatalogItem("truck", "Truck"),
    TransportModeCatalogItem("van", "Van"),
    TransportModeCatalogItem("bus", "Bus"),
)

TRANSPORT_QUALIFICATION_TYPES_CANONICAL: Final[tuple[TransportQualificationTypeCatalogItem, ...]] = (
    TransportQualificationTypeCatalogItem("driver_license", "Driver License"),
    TransportQualificationTypeCatalogItem("code_95", "Code 95"),
    TransportQualificationTypeCatalogItem("tachograph_card", "Tachograph Card"),
)

DRIVER_CAPABILITY_CLASSES_CANONICAL: Final[tuple[DriverCapabilityClassCatalogItem, ...]] = (
    DriverCapabilityClassCatalogItem("B", "Passenger Car"),
    DriverCapabilityClassCatalogItem("C", "Truck"),
    DriverCapabilityClassCatalogItem("CE", "Truck + Trailer"),
    DriverCapabilityClassCatalogItem("D", "Bus"),
)


def _normalize_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _normalize_driver_capability(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


WORKFORCE_CATEGORIES_BY_CODE: Final[dict[str, WorkforceCategoryCatalogItem]] = {
    item.code: item for item in WORKFORCE_CATEGORIES_CANONICAL
}
EMPLOYMENT_TYPES_BY_CODE: Final[dict[str, EmploymentTypeCatalogItem]] = {
    item.code: item for item in EMPLOYMENT_TYPES_CANONICAL
}
TRANSPORT_MODES_BY_CODE: Final[dict[str, TransportModeCatalogItem]] = {
    item.code: item for item in TRANSPORT_MODES_CANONICAL
}
TRANSPORT_QUALIFICATION_TYPES_BY_CODE: Final[dict[str, TransportQualificationTypeCatalogItem]] = {
    item.code: item for item in TRANSPORT_QUALIFICATION_TYPES_CANONICAL
}
DRIVER_CAPABILITY_CLASSES_BY_CODE: Final[dict[str, DriverCapabilityClassCatalogItem]] = {
    item.code: item for item in DRIVER_CAPABILITY_CLASSES_CANONICAL
}


def list_workforce_categories_canonical() -> tuple[WorkforceCategoryCatalogItem, ...]:
    return WORKFORCE_CATEGORIES_CANONICAL


def list_employment_types_canonical() -> tuple[EmploymentTypeCatalogItem, ...]:
    return EMPLOYMENT_TYPES_CANONICAL


def list_transport_modes_canonical() -> tuple[TransportModeCatalogItem, ...]:
    return TRANSPORT_MODES_CANONICAL


def list_transport_qualification_types_canonical() -> tuple[TransportQualificationTypeCatalogItem, ...]:
    return TRANSPORT_QUALIFICATION_TYPES_CANONICAL


def list_driver_capability_classes_canonical() -> tuple[DriverCapabilityClassCatalogItem, ...]:
    return DRIVER_CAPABILITY_CLASSES_CANONICAL


def get_workforce_category_by_code(code: str | None) -> WorkforceCategoryCatalogItem | None:
    normalized = _normalize_code(code)
    if normalized is None:
        return None
    return WORKFORCE_CATEGORIES_BY_CODE.get(normalized)


def get_transport_mode_by_code(code: str | None) -> TransportModeCatalogItem | None:
    normalized = _normalize_code(code)
    if normalized is None:
        return None
    return TRANSPORT_MODES_BY_CODE.get(normalized)


def get_driver_capability_class_by_code(code: str | None) -> DriverCapabilityClassCatalogItem | None:
    normalized = _normalize_driver_capability(code)
    if normalized is None:
        return None
    return DRIVER_CAPABILITY_CLASSES_BY_CODE.get(normalized)


def _assert_unique_codes() -> None:
    collections = (
        [item.code for item in WORKFORCE_CATEGORIES_CANONICAL],
        [item.code for item in EMPLOYMENT_TYPES_CANONICAL],
        [item.code for item in TRANSPORT_MODES_CANONICAL],
        [item.code for item in TRANSPORT_QUALIFICATION_TYPES_CANONICAL],
        [item.code for item in DRIVER_CAPABILITY_CLASSES_CANONICAL],
    )
    for values in collections:
        assert len(values) == len(set(values)), "Duplicate canonical code in workforce/transport catalogs"


_assert_unique_codes()


__all__ = [
    "CATALOG_VERSION",
    "WorkforceCategoryCatalogItem",
    "EmploymentTypeCatalogItem",
    "TransportModeCatalogItem",
    "TransportQualificationTypeCatalogItem",
    "DriverCapabilityClassCatalogItem",
    "WORKFORCE_CATEGORIES_CANONICAL",
    "EMPLOYMENT_TYPES_CANONICAL",
    "TRANSPORT_MODES_CANONICAL",
    "TRANSPORT_QUALIFICATION_TYPES_CANONICAL",
    "DRIVER_CAPABILITY_CLASSES_CANONICAL",
    "list_workforce_categories_canonical",
    "list_employment_types_canonical",
    "list_transport_modes_canonical",
    "list_transport_qualification_types_canonical",
    "list_driver_capability_classes_canonical",
    "get_workforce_category_by_code",
    "get_transport_mode_by_code",
    "get_driver_capability_class_by_code",
]
