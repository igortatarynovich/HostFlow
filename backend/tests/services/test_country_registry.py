from __future__ import annotations

import json
import re
from pathlib import Path

from backend.app.constants.catalogs import COUNTRIES, DIAL_CODES
from backend.app.reference.country_registry import (
    FORBIDDEN_IDENTITY_CODES,
    ISO_3166_1_ASSIGNED_COUNT,
    REGISTRY_PATH,
    country_registry_alpha2_set,
    get_country_registry_entry,
    list_country_registry_entries,
    load_registry_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_COUNTRIES = REPO_ROOT / "hostflow-frontend" / "src" / "data" / "countries.ts"
ISO_CODES_PATH = Path("/usr/share/iso-codes/json/iso_3166-1.json")


def _frontend_country_codes() -> set[str]:
    text = FRONTEND_COUNTRIES.read_text(encoding="utf-8")
    return set(re.findall(r"'([A-Z]{2})'", text))


def test_country_registry_is_full_iso_3166_1_assigned_set() -> None:
    entries = list_country_registry_entries()
    alpha2 = country_registry_alpha2_set()
    assert len(entries) == ISO_3166_1_ASSIGNED_COUNT
    assert len(alpha2) == ISO_3166_1_ASSIGNED_COUNT
    payload = load_registry_payload()
    assert payload["iso_standard"] == "ISO 3166-1"
    assert REGISTRY_PATH.is_file()


def test_country_registry_matches_debian_iso_codes_when_present() -> None:
    if not ISO_CODES_PATH.is_file():
        return
    raw = json.loads(ISO_CODES_PATH.read_text(encoding="utf-8"))
    official = {row["alpha_2"] for row in raw["3166-1"]}
    assert country_registry_alpha2_set() == official
    assert "XK" not in official


def test_country_registry_identity_and_labels_contract() -> None:
    pl = get_country_registry_entry("pl")
    assert pl is not None
    assert pl.identity.alpha2 == "PL"
    assert pl.identity.alpha3 == "POL"
    assert pl.identity.numeric == "616"
    assert pl.labels.en == "Poland"
    assert pl.labels.pl == "Polska"
    assert pl.labels.ru == "Польша"
    assert pl.classifications.dial_code == "+48"
    assert pl.classifications.eu_member is True
    assert pl.classifications.schengen_member is True


def test_country_registry_forbidden_codes_not_in_canon() -> None:
    alpha2 = country_registry_alpha2_set()
    assert alpha2.isdisjoint(FORBIDDEN_IDENTITY_CODES)
    assert get_country_registry_entry("XK") is None
    assert get_country_registry_entry("OTHER") is None
    assert get_country_registry_entry("UK") is None
    assert get_country_registry_entry("GB") is not None


def test_country_registry_dial_code_is_not_unique() -> None:
    us = get_country_registry_entry("US")
    ca = get_country_registry_entry("CA")
    assert us is not None and ca is not None
    assert us.classifications.dial_code == "+1"
    assert ca.classifications.dial_code == "+1"
    dials = [e.classifications.dial_code for e in list_country_registry_entries()]
    assert len(dials) != len(set(dials))


def test_country_registry_does_not_auto_promote_discovery_union() -> None:
    """Legacy lists are discovery input only — they cannot extend canon."""
    discovery = set(COUNTRIES) | set(DIAL_CODES) | _frontend_country_codes()
    canon = country_registry_alpha2_set()
    assert "XK" in discovery
    assert "XK" not in canon
    extras = discovery - canon
    assert extras <= FORBIDDEN_IDENTITY_CODES | {"XK"}


def test_country_registry_json_has_no_immutable_keys() -> None:
    blob = REGISTRY_PATH.read_text(encoding="utf-8")
    assert "immutable" not in blob.lower()
