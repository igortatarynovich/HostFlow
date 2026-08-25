"""Tests for company setup reference catalogs and catalog API helpers."""

from __future__ import annotations

from backend.app.constants.catalog_utils import to_options_localized_catalog
from backend.app.reference.company_setup_catalogs import (
    INDUSTRY_CODES,
    list_industries,
    list_vacancy_search_categories,
)
from backend.app.reference.geo_cities_catalog import list_cities


def test_industries_catalog_has_expanded_set():
    codes = {item.code for item in list_industries()}
    assert "transport_logistics" in codes
    assert "education" in codes
    assert codes == INDUSTRY_CODES


def test_vacancy_search_categories_launch_search_subset():
    all_rows = list_vacancy_search_categories(launch_search_only=False)
    launch_rows = list_vacancy_search_categories(launch_search_only=True)
    assert len(launch_rows) >= 4
    assert len(all_rows) >= len(launch_rows)
    assert all(item.meta.get("launch_search_supported") for item in launch_rows)


def test_cities_filtered_by_country():
    pl = list_cities(country_code="PL")
    de = list_cities(country_code="DE")
    assert pl
    assert de
    assert all(item.country_code == "PL" for item in pl)


def test_to_options_localized_catalog_shape():
    rows = to_options_localized_catalog(list_industries())
    assert rows[0]["value"]
    assert rows[0]["label"]
    assert rows[0]["meta"]["label_en"]
