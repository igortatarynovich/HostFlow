from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CountryCatalogItem:
    code_alpha2: str
    code_alpha3: str
    code_numeric: str
    name: str


@dataclass(frozen=True)
class LanguageCatalogItem:
    code: str
    name: str


CATALOG_VERSION: Final[str] = "ref4-phase1a-core-immutable-v1"


# Phase 1A scope: immutable baseline identity only.
COUNTRIES_IMMUTABLE: Final[tuple[CountryCatalogItem, ...]] = (
    CountryCatalogItem("PL", "POL", "616", "Poland"),
    CountryCatalogItem("DE", "DEU", "276", "Germany"),
    CountryCatalogItem("UA", "UKR", "804", "Ukraine"),
)

LANGUAGE_CODES_IMMUTABLE: Final[tuple[LanguageCatalogItem, ...]] = (
    LanguageCatalogItem("en", "English"),
    LanguageCatalogItem("pl", "Polish"),
    LanguageCatalogItem("uk", "Ukrainian"),
)


COUNTRIES_BY_ALPHA2: Final[dict[str, CountryCatalogItem]] = {
    item.code_alpha2: item for item in COUNTRIES_IMMUTABLE
}

LANGUAGES_BY_CODE: Final[dict[str, LanguageCatalogItem]] = {
    item.code: item for item in LANGUAGE_CODES_IMMUTABLE
}


def normalize_country_alpha2(code: str | None) -> str | None:
    if code is None:
        return None
    value = str(code).strip().upper()
    return value or None


def normalize_language_code(code: str | None) -> str | None:
    if code is None:
        return None
    value = str(code).strip().lower()
    return value or None


def get_country_by_alpha2(code: str | None) -> CountryCatalogItem | None:
    normalized = normalize_country_alpha2(code)
    if normalized is None:
        return None
    return COUNTRIES_BY_ALPHA2.get(normalized)


def get_language_by_code(code: str | None) -> LanguageCatalogItem | None:
    normalized = normalize_language_code(code)
    if normalized is None:
        return None
    return LANGUAGES_BY_CODE.get(normalized)


def list_countries_immutable() -> tuple[CountryCatalogItem, ...]:
    return COUNTRIES_IMMUTABLE


def list_languages_immutable() -> tuple[LanguageCatalogItem, ...]:
    return LANGUAGE_CODES_IMMUTABLE


def _assert_unique_countries() -> None:
    alpha2 = [item.code_alpha2 for item in COUNTRIES_IMMUTABLE]
    alpha3 = [item.code_alpha3 for item in COUNTRIES_IMMUTABLE]
    numeric = [item.code_numeric for item in COUNTRIES_IMMUTABLE]
    assert len(alpha2) == len(set(alpha2)), "Duplicate country alpha2 code in immutable catalog"
    assert len(alpha3) == len(set(alpha3)), "Duplicate country alpha3 code in immutable catalog"
    assert len(numeric) == len(set(numeric)), "Duplicate country numeric code in immutable catalog"


def _assert_unique_languages() -> None:
    codes = [item.code for item in LANGUAGE_CODES_IMMUTABLE]
    assert len(codes) == len(set(codes)), "Duplicate language code in immutable catalog"


_assert_unique_countries()
_assert_unique_languages()


__all__ = [
    "CATALOG_VERSION",
    "CountryCatalogItem",
    "LanguageCatalogItem",
    "COUNTRIES_IMMUTABLE",
    "LANGUAGE_CODES_IMMUTABLE",
    "COUNTRIES_BY_ALPHA2",
    "LANGUAGES_BY_CODE",
    "normalize_country_alpha2",
    "normalize_language_code",
    "get_country_by_alpha2",
    "get_language_by_code",
    "list_countries_immutable",
    "list_languages_immutable",
]
