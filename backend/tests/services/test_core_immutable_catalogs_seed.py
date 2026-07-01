from __future__ import annotations

from backend.app.reference.core_immutable_catalogs_seed import (
    SEED_ID,
    build_immutable_catalog_seed_payload,
    immutable_catalog_seed_checksum,
)


def test_core_immutable_seed_payload_shape() -> None:
    payload = build_immutable_catalog_seed_payload()
    assert payload.catalog_version.startswith("ref4-phase1a-core-immutable-")
    assert len(payload.countries) >= 1
    assert len(payload.languages) >= 1
    assert SEED_ID == "ref4_phase1a_core_immutable_seed_v1"


def test_core_immutable_seed_checksum_is_deterministic() -> None:
    p1 = build_immutable_catalog_seed_payload()
    p2 = build_immutable_catalog_seed_payload()
    assert immutable_catalog_seed_checksum(p1) == immutable_catalog_seed_checksum(p2)

