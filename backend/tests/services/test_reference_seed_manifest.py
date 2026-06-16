from __future__ import annotations

from backend.app.reference.reference_seed_manifest import (
    CATALOG_VERSION,
    compose_deterministic_seed_checksum,
    get_reference_version_manifest,
    list_seed_manifest_entries,
)


def test_reference_seed_manifest_baseline_shape() -> None:
    assert CATALOG_VERSION.startswith("ref4-phase1c-seed-manifest-")
    entries = list_seed_manifest_entries()
    versions = get_reference_version_manifest()
    assert len(entries) >= 1
    assert len(versions) >= 1
    assert {item.domain for item in entries} == set(versions.keys())


def test_reference_seed_manifest_checksum_is_deterministic() -> None:
    c1 = compose_deterministic_seed_checksum()
    c2 = compose_deterministic_seed_checksum()
    assert c1 == c2
    assert len(c1) == 64
