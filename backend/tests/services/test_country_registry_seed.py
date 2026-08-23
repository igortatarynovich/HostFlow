from __future__ import annotations

from backend.app.reference.country_registry_seed import (
    SEED_ID,
    build_country_registry_seed_payload,
    country_registry_seed_checksum,
)


def test_country_registry_seed_payload_shape() -> None:
    payload = build_country_registry_seed_payload()
    assert payload.catalog_version.startswith("ref-id-r1-country-registry-")
    assert len(payload.countries) == 249
    assert SEED_ID == "ref_id_r1_country_registry_seed_v1"


def test_country_registry_seed_checksum_is_deterministic() -> None:
    p1 = build_country_registry_seed_payload()
    p2 = build_country_registry_seed_payload()
    c1 = country_registry_seed_checksum(p1)
    c2 = country_registry_seed_checksum(p2)
    assert c1 == c2
    assert len(c1) == 64
    assert country_registry_seed_checksum() == c1
