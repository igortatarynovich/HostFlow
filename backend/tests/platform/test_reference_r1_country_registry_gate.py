"""Reference R1 — Country Registry Gate.

Authoritative ISO 3166-1 assigned Country Registry (identity / classifications /
labels). Facade snapshot only. catalogs.py stays runtime SoT (cutover is R2).
XK / OTHER / UK not in canon. dial_code is not unique. No Postgres required.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from backend.app.api.v1 import catalogs as catalogs_api
from backend.app.reference.country_registry import (
    FORBIDDEN_IDENTITY_CODES,
    ISO_3166_1_ASSIGNED_COUNT,
    REGISTRY_PATH,
    country_registry_alpha2_set,
    get_country_registry_entry,
    list_country_registry_entries,
)
from backend.app.reference.country_registry_seed import (
    build_country_registry_seed_payload,
    country_registry_seed_checksum,
)
from backend.app.schemas.reference_country_registry import CountryRegistrySnapshotOut
from backend.app.services.reference_service_facade import ReferenceServiceFacade

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "platform-reference-identity-sot.md"
_JSON = _REPO_ROOT / "docs" / "specs" / "platform" / "country-registry-v1.json"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_SCHEMA = (
    _REPO_ROOT / "backend" / "app" / "schemas" / "reference_country_registry.py"
)
_CATALOGS = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "catalogs.py"


def test_r1_brief_and_json_exist() -> None:
    assert _BRIEF.is_file()
    assert _JSON.is_file()
    assert REGISTRY_PATH.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Reference R1 Country Registry Gate" in brief
    assert "zero runtime consumer cutover" in brief.lower()


def test_r1_iso_assigned_set_and_forbidden_codes() -> None:
    entries = list_country_registry_entries()
    alpha2 = country_registry_alpha2_set()
    assert len(entries) == ISO_3166_1_ASSIGNED_COUNT
    assert len(alpha2) == ISO_3166_1_ASSIGNED_COUNT
    assert alpha2.isdisjoint(FORBIDDEN_IDENTITY_CODES)
    assert get_country_registry_entry("XK") is None
    assert get_country_registry_entry("OTHER") is None
    assert get_country_registry_entry("UK") is None
    assert get_country_registry_entry("GB") is not None
    pl = get_country_registry_entry("PL")
    assert pl is not None
    assert pl.labels.en and pl.labels.pl and pl.labels.ru
    assert pl.classifications.dial_code == "+48"


def test_r1_facade_snapshot_identity_classifications_labels_only() -> None:
    snapshot = ReferenceServiceFacade.get_country_registry_snapshot()
    parsed = CountryRegistrySnapshotOut.model_validate(snapshot)
    assert len(parsed.countries) == ISO_3166_1_ASSIGNED_COUNT
    row = next(c for c in parsed.countries if c.identity.alpha2 == "PL")
    dump = row.model_dump()
    assert set(dump) == {"identity", "classifications", "labels"}
    assert "immutable" not in dump
    schema = _SCHEMA.read_text(encoding="utf-8")
    assert "immutable" not in schema
    check = ReferenceServiceFacade.compatibility_check_country_registry_snapshot()
    assert check["valid"] is True
    assert check["errors"] == []


def test_r1_dial_code_is_not_unique() -> None:
    us = get_country_registry_entry("US")
    ca = get_country_registry_entry("CA")
    assert us is not None and ca is not None
    assert us.classifications.dial_code == ca.classifications.dial_code == "+1"
    dials = [e.classifications.dial_code for e in list_country_registry_entries()]
    assert len(dials) != len(set(dials))


def test_r1_does_not_cut_over_runtime_catalogs() -> None:
    source = inspect.getsource(catalogs_api)
    catalogs = _CATALOGS.read_text(encoding="utf-8")
    assert "backend.app.constants.catalogs import COUNTRIES" in source
    assert "country_registry" not in source
    assert "country_registry" not in catalogs


def test_r1_seed_checksum_is_deterministic() -> None:
    p1 = build_country_registry_seed_payload()
    p2 = build_country_registry_seed_payload()
    assert country_registry_seed_checksum(p1) == country_registry_seed_checksum(p2)
    assert len(country_registry_seed_checksum(p1)) == 64
    assert len(p1.countries) == ISO_3166_1_ASSIGNED_COUNT


def test_r1_named_ci_gate_and_agents() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Reference R1 Country Registry Gate" in ci
    assert "test_reference_r1_country_registry_gate.py" in ci
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "platform-reference-identity-sot.md" in agents
    assert "named Country Registry Gate" in agents
    queue = (
        _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    assert "platform-reference-identity-sot.md" in queue


def test_r1_gate_filename() -> None:
    assert Path(__file__).name == "test_reference_r1_country_registry_gate.py"
