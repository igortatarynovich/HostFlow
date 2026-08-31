"""Tests for company setup reference catalogs and catalog API helpers."""

from __future__ import annotations

import asyncio

from backend.app.constants.catalog_utils import (
    to_options_company_setup,
    to_options_countries,
    to_options_localized_catalog,
)
from backend.app.reference.company_setup_catalogs import (
    INDUSTRY_CODES,
    TEAM_SIZE_CODES,
    TEAM_SIZE_ONBOARDING_CODES,
    list_business_types,
    list_first_modules,
    list_industries,
    list_platform_identities,
    list_team_sizes,
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


def test_list_team_sizes_accepts_onboarding_flag():
    default_codes = {item.code for item in list_team_sizes()}
    onboarding_codes = {item.code for item in list_team_sizes(onboarding=True)}
    assert default_codes == TEAM_SIZE_CODES
    assert onboarding_codes == TEAM_SIZE_ONBOARDING_CODES
    assert "2_10" in default_codes
    assert "2_5" in onboarding_codes
    assert "2_5" not in default_codes


def test_list_company_setup_options_endpoint_does_not_raise():
    from backend.app.api.v1.catalogs import list_company_setup_options

    payload = asyncio.run(list_company_setup_options())
    assert {row["value"] for row in payload["team_sizes"]} == TEAM_SIZE_CODES


def test_company_setup_options_payload_matches_api_composition():
    payload = to_options_company_setup(
        countries=to_options_countries(),
        industries=to_options_localized_catalog(list_industries()),
        team_sizes=to_options_localized_catalog(list_team_sizes(onboarding=False)),
        platform_identities=to_options_localized_catalog(list_platform_identities()),
        first_modules=to_options_localized_catalog(list_first_modules()),
        business_types=to_options_localized_catalog(list_business_types()),
    )
    assert payload["countries"]
    assert payload["industries"]
    assert {row["value"] for row in payload["team_sizes"]} == TEAM_SIZE_CODES
    assert payload["platform_identities"]
    assert payload["first_modules"]
    assert payload["business_types"]
