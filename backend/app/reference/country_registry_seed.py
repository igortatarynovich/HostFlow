"""Deterministic seed checksum for the Country Registry (Reference R1).

Checksum covers the authoritative JSON definition. No DB write — R1 does not
cut over runtime consumers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Final

from backend.app.reference.country_registry import (
    CATALOG_VERSION,
    load_registry_payload,
)

SEED_ID: Final[str] = "ref_id_r1_country_registry_seed_v1"


@dataclass(frozen=True)
class CountryRegistrySeedPayload:
    catalog_version: str
    registry_version: str
    countries: tuple[dict[str, Any], ...]


def build_country_registry_seed_payload() -> CountryRegistrySeedPayload:
    payload = load_registry_payload()
    countries = tuple(payload.get("countries") or [])
    return CountryRegistrySeedPayload(
        catalog_version=CATALOG_VERSION,
        registry_version=str(payload.get("registry_version") or ""),
        countries=countries,
    )


def country_registry_seed_checksum(payload: CountryRegistrySeedPayload | None = None) -> str:
    p = payload or build_country_registry_seed_payload()
    canonical = {
        "catalog_version": p.catalog_version,
        "registry_version": p.registry_version,
        "countries": list(p.countries),
    }
    blob = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


__all__ = [
    "SEED_ID",
    "CountryRegistrySeedPayload",
    "build_country_registry_seed_payload",
    "country_registry_seed_checksum",
]
