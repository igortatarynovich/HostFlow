"""Resolve platform library options for intake presentation fields."""

from __future__ import annotations

from typing import Any

from backend.app.constants.catalogs import COUNTRIES
from backend.app.constants.catalog_utils import to_options_countries, to_options_localized_catalog
from backend.app.reference.geo_cities_catalog import list_cities
from backend.app.reference.questionnaire_catalogs import (
    list_advertised_services,
    list_professions,
    list_regions,
)

REFERENCE_DOMAIN_COUNTRIES = "countries"
REFERENCE_DOMAIN_REGIONS = "regions"
REFERENCE_DOMAIN_CITIES = "cities"
REFERENCE_DOMAIN_PROFESSIONS = "professions"
REFERENCE_DOMAIN_SERVICES = "services"


def _options_from_countries() -> list[dict[str, str]]:
    return to_options_countries()


def _options_from_regions(*, country_code: str | None = None) -> list[dict[str, str]]:
    return to_options_localized_catalog(list_regions(country_code=country_code))


def _options_from_cities(*, country_code: str | None = None) -> list[dict[str, str]]:
    return to_options_localized_catalog(list_cities(country_code=country_code))


def _options_from_professions() -> list[dict[str, str]]:
    return to_options_localized_catalog(list_professions())


def _options_from_services() -> list[dict[str, str]]:
    return to_options_localized_catalog(list_advertised_services())


def reference_domain_options(
    reference_domain: str | None,
    *,
    country_code: str | None = None,
) -> list[dict[str, str]]:
    domain = str(reference_domain or "").strip().lower()
    if domain == REFERENCE_DOMAIN_COUNTRIES:
        return _options_from_countries()
    if domain == REFERENCE_DOMAIN_REGIONS:
        return _options_from_regions(country_code=country_code)
    if domain == REFERENCE_DOMAIN_CITIES:
        return _options_from_cities(country_code=country_code)
    if domain == REFERENCE_DOMAIN_PROFESSIONS:
        return _options_from_professions()
    if domain == REFERENCE_DOMAIN_SERVICES:
        return _options_from_services()
    return []


def attach_reference_metadata(field_row: dict[str, Any]) -> dict[str, Any]:
    """Attach ``reference_domain`` and optional ``reference_filter`` from embedded field registry row."""
    row = dict(field_row)
    embedded = row.get("field") if isinstance(row.get("field"), dict) else {}
    reference_domain = str(embedded.get("reference_domain") or "").strip() or None
    if reference_domain:
        row["reference_domain"] = reference_domain
    meta = embedded.get("reference_meta")
    if isinstance(meta, dict) and meta:
        row["reference_meta"] = dict(meta)
    return row


def attach_library_options_to_presentation_field(field_row: dict[str, Any]) -> dict[str, Any]:
    """Populate ``options`` from platform reference domain when field is library-backed."""
    row = attach_reference_metadata(field_row)
    embedded = row.get("field") if isinstance(row.get("field"), dict) else {}
    reference_domain = str(row.get("reference_domain") or embedded.get("reference_domain") or "").strip()
    if not reference_domain:
        return row
    meta = row.get("reference_meta")
    if isinstance(meta, dict) and meta.get("depends_on_field"):
        # Cascading library — public UI loads options after parent selection.
        return row
    field_type = str(row.get("field_type") or row.get("widget_hint") or "").lower()
    if "select" not in field_type and reference_domain not in {
        REFERENCE_DOMAIN_COUNTRIES,
        REFERENCE_DOMAIN_REGIONS,
        REFERENCE_DOMAIN_CITIES,
    }:
        return row
    options = reference_domain_options(reference_domain)
    if options:
        row["options"] = options
    return row
