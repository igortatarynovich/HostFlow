from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Final

from backend.app.reference.core_immutable_catalogs import (
    CATALOG_VERSION,
    COUNTRIES_IMMUTABLE,
    LANGUAGE_CODES_IMMUTABLE,
)


@dataclass(frozen=True)
class ImmutableCatalogSeedPayload:
    catalog_version: str
    countries: tuple[dict[str, str], ...]
    languages: tuple[dict[str, str], ...]


SEED_ID: Final[str] = "ref4_phase1a_core_immutable_seed_v1"


def build_immutable_catalog_seed_payload() -> ImmutableCatalogSeedPayload:
    countries = tuple(
        {
            "code_alpha2": item.code_alpha2,
            "code_alpha3": item.code_alpha3,
            "code_numeric": item.code_numeric,
            "name": item.name,
        }
        for item in COUNTRIES_IMMUTABLE
    )
    languages = tuple(
        {
            "code": item.code,
            "name": item.name,
        }
        for item in LANGUAGE_CODES_IMMUTABLE
    )
    return ImmutableCatalogSeedPayload(
        catalog_version=CATALOG_VERSION,
        countries=countries,
        languages=languages,
    )


def immutable_catalog_seed_checksum(payload: ImmutableCatalogSeedPayload | None = None) -> str:
    p = payload or build_immutable_catalog_seed_payload()
    canonical_json = json.dumps(asdict(p), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


__all__ = [
    "SEED_ID",
    "ImmutableCatalogSeedPayload",
    "build_immutable_catalog_seed_payload",
    "immutable_catalog_seed_checksum",
]

