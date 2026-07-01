from __future__ import annotations

from backend.app.reference.core_immutable_catalogs import (
    CATALOG_VERSION,
    COUNTRIES_IMMUTABLE,
    LANGUAGE_CODES_IMMUTABLE,
    get_country_by_alpha2,
    get_language_by_code,
    list_countries_immutable,
    list_languages_immutable,
)


def test_core_immutable_catalogs_basic_shape() -> None:
    assert CATALOG_VERSION.startswith("ref4-phase1a-core-immutable-")
    assert len(COUNTRIES_IMMUTABLE) >= 1
    assert len(LANGUAGE_CODES_IMMUTABLE) >= 1


def test_core_immutable_catalog_lookup_and_normalization() -> None:
    assert get_country_by_alpha2("pl") is not None
    assert get_country_by_alpha2(" PL ") is not None
    assert get_country_by_alpha2(None) is None

    assert get_language_by_code("EN") is not None
    assert get_language_by_code(" en ") is not None
    assert get_language_by_code(None) is None


def test_core_immutable_catalog_iterables() -> None:
    countries = list_countries_immutable()
    languages = list_languages_immutable()
    assert isinstance(countries, tuple)
    assert isinstance(languages, tuple)
    assert countries == COUNTRIES_IMMUTABLE
    assert languages == LANGUAGE_CODES_IMMUTABLE

