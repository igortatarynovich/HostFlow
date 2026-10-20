"""Closed catalogs introduced for the professional-profile schema.

Driving categories stay on the existing ``driver_license_categories`` reference
domain. Work-system and pay-period codes stay on the hiring field catalog.
Trailer vocabularies are not merged here. This module owns only the new
closed sets. ``professional_code_mappings`` starts empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ProfessionalCatalogCode:
    vocabulary: str
    code: str


OPERATION_SCOPE: Final[str] = "operation_scope"
MOVEMENT_PATTERN: Final[str] = "movement_pattern"
CREW_MODE: Final[str] = "crew_mode"
WORK_AREA_REGION: Final[str] = "work_area_region"

PROFESSIONAL_CATALOG_CODES: Final[tuple[ProfessionalCatalogCode, ...]] = (
    ProfessionalCatalogCode(OPERATION_SCOPE, "international"),
    ProfessionalCatalogCode(OPERATION_SCOPE, "domestic"),
    ProfessionalCatalogCode(MOVEMENT_PATTERN, "long_haul"),
    ProfessionalCatalogCode(MOVEMENT_PATTERN, "distribution"),
    ProfessionalCatalogCode(CREW_MODE, "solo"),
    ProfessionalCatalogCode(CREW_MODE, "double"),
    ProfessionalCatalogCode(WORK_AREA_REGION, "eu"),
    ProfessionalCatalogCode(WORK_AREA_REGION, "cis"),
    ProfessionalCatalogCode(WORK_AREA_REGION, "uk"),
    ProfessionalCatalogCode(WORK_AREA_REGION, "scandi"),
    ProfessionalCatalogCode(WORK_AREA_REGION, "local"),
)

TRAILER_VOCABULARIES: Final[tuple[str, ...]] = (
    "trailer_intake",
    "trailer_hiring",
    "trailer_employment_raw",
)


def catalog_code_pairs() -> tuple[tuple[str, str], ...]:
    return tuple((item.vocabulary, item.code) for item in PROFESSIONAL_CATALOG_CODES)


__all__ = [
    "CREW_MODE",
    "MOVEMENT_PATTERN",
    "OPERATION_SCOPE",
    "PROFESSIONAL_CATALOG_CODES",
    "ProfessionalCatalogCode",
    "TRAILER_VOCABULARIES",
    "WORK_AREA_REGION",
    "catalog_code_pairs",
]
