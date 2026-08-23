"""Platform Country Registry — Reference R1 authoritative definition.

JSON at ``docs/specs/platform/country-registry-v1.json`` is the identity SoT.
This module is the in-process loader and contract surface. It does **not**
replace ``constants/catalogs.py`` as runtime SoT (that cutover is Reference R2).

Public vocabulary: ``identity`` | ``classifications`` | ``labels``.
Do not expose ``immutable`` on this contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Optional

_SPECS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "specs" / "platform"
REGISTRY_PATH = _SPECS_ROOT / "country-registry-v1.json"

CATALOG_VERSION: Final[str] = "ref-id-r1-country-registry-v1"

_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")
_ALPHA3_RE = re.compile(r"^[A-Z]{3}$")
_NUMERIC_RE = re.compile(r"^[0-9]{3}$")
_DIAL_RE = re.compile(r"^\+[0-9]{1,7}$")

FORBIDDEN_IDENTITY_CODES: Final[frozenset[str]] = frozenset({"XK", "UK", "OTHER"})
REQUIRED_LABEL_LOCALES: Final[tuple[str, ...]] = ("en", "pl", "ru")
ISO_3166_1_ASSIGNED_COUNT: Final[int] = 249


@dataclass(frozen=True)
class CountryIdentity:
    alpha2: str
    alpha3: str
    numeric: str


@dataclass(frozen=True)
class CountryClassifications:
    dial_code: str
    eu_member: bool
    schengen_member: bool


@dataclass(frozen=True)
class CountryLabels:
    en: str
    pl: str
    ru: str


@dataclass(frozen=True)
class CountryRegistryEntry:
    identity: CountryIdentity
    classifications: CountryClassifications
    labels: CountryLabels


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Country registry payload must be an object: {path}")
    return payload


@lru_cache(maxsize=1)
def load_registry_payload() -> dict[str, Any]:
    return _load_json(REGISTRY_PATH)


def _entry_from_raw(raw: dict[str, Any]) -> CountryRegistryEntry:
    labels_raw = raw.get("labels") or {}
    return CountryRegistryEntry(
        identity=CountryIdentity(
            alpha2=str(raw["alpha2"]).strip().upper(),
            alpha3=str(raw["alpha3"]).strip().upper(),
            numeric=str(raw["numeric"]).strip().zfill(3),
        ),
        classifications=CountryClassifications(
            dial_code=str(raw["dial_code"]).strip(),
            eu_member=bool(raw.get("eu_member")),
            schengen_member=bool(raw.get("schengen_member")),
        ),
        labels=CountryLabels(
            en=str(labels_raw.get("en") or "").strip(),
            pl=str(labels_raw.get("pl") or "").strip(),
            ru=str(labels_raw.get("ru") or "").strip(),
        ),
    )


@lru_cache(maxsize=1)
def list_country_registry_entries() -> tuple[CountryRegistryEntry, ...]:
    payload = load_registry_payload()
    rows = payload.get("countries") or []
    return tuple(_entry_from_raw(row) for row in rows)


@lru_cache(maxsize=1)
def country_registry_by_alpha2() -> dict[str, CountryRegistryEntry]:
    return {entry.identity.alpha2: entry for entry in list_country_registry_entries()}


def get_country_registry_entry(alpha2: str | None) -> Optional[CountryRegistryEntry]:
    if alpha2 is None:
        return None
    key = str(alpha2).strip().upper()
    if not key:
        return None
    return country_registry_by_alpha2().get(key)


def country_registry_alpha2_set() -> frozenset[str]:
    return frozenset(country_registry_by_alpha2().keys())


def _assert_registry_invariants() -> None:
    entries = list_country_registry_entries()
    assert len(entries) == ISO_3166_1_ASSIGNED_COUNT, (
        f"Country registry must contain the ISO 3166-1 assigned set "
        f"({ISO_3166_1_ASSIGNED_COUNT} codes), got {len(entries)}"
    )

    alpha2_list = [e.identity.alpha2 for e in entries]
    alpha3_list = [e.identity.alpha3 for e in entries]
    numeric_list = [e.identity.numeric for e in entries]
    assert len(alpha2_list) == len(set(alpha2_list)), "Duplicate country alpha2 in registry"
    assert len(alpha3_list) == len(set(alpha3_list)), "Duplicate country alpha3 in registry"
    assert len(numeric_list) == len(set(numeric_list)), "Duplicate country numeric in registry"

    identity_set = set(alpha2_list)
    leak = identity_set & FORBIDDEN_IDENTITY_CODES
    assert not leak, f"Forbidden identity codes in Country Registry: {sorted(leak)}"

    for entry in entries:
        ident = entry.identity
        assert _ALPHA2_RE.match(ident.alpha2), f"Invalid alpha2: {ident.alpha2!r}"
        assert _ALPHA3_RE.match(ident.alpha3), f"Invalid alpha3: {ident.alpha3!r}"
        assert _NUMERIC_RE.match(ident.numeric), f"Invalid numeric: {ident.numeric!r}"
        assert _DIAL_RE.match(entry.classifications.dial_code), (
            f"Invalid dial_code for {ident.alpha2}: {entry.classifications.dial_code!r}"
        )
        for locale in REQUIRED_LABEL_LOCALES:
            label = getattr(entry.labels, locale)
            assert label, f"Missing {locale} label for {ident.alpha2}"

    dial_codes = [e.classifications.dial_code for e in entries]
    assert len(dial_codes) != len(set(dial_codes)), (
        "dial_code must not be unique: NANP/shared codes are required (US/CA → +1)"
    )
    us = country_registry_by_alpha2()["US"]
    ca = country_registry_by_alpha2()["CA"]
    pl = country_registry_by_alpha2()["PL"]
    assert us.classifications.dial_code == "+1"
    assert ca.classifications.dial_code == "+1"
    assert pl.classifications.dial_code == "+48"


_assert_registry_invariants()


__all__ = [
    "CATALOG_VERSION",
    "REGISTRY_PATH",
    "FORBIDDEN_IDENTITY_CODES",
    "REQUIRED_LABEL_LOCALES",
    "ISO_3166_1_ASSIGNED_COUNT",
    "CountryIdentity",
    "CountryClassifications",
    "CountryLabels",
    "CountryRegistryEntry",
    "load_registry_payload",
    "list_country_registry_entries",
    "country_registry_by_alpha2",
    "get_country_registry_entry",
    "country_registry_alpha2_set",
]
