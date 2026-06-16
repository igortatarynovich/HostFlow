from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from backend.app.reference.core_immutable_catalogs import CATALOG_VERSION as CORE_IMMUTABLE_CATALOG_VERSION
from backend.app.reference.legal_document_catalogs import CATALOG_VERSION as LEGAL_DOCUMENT_CATALOG_VERSION
from backend.app.reference.reference_field_schema_registry import CATALOG_VERSION as FIELD_SCHEMA_CATALOG_VERSION
from backend.app.reference.reference_rule_pack_foundation import CATALOG_VERSION as RULE_PACK_FOUNDATION_CATALOG_VERSION
from backend.app.reference.reference_tenant_override_foundation import (
    CATALOG_VERSION as TENANT_OVERRIDE_FOUNDATION_CATALOG_VERSION,
)
from backend.app.reference.workforce_transport_catalogs import (
    CATALOG_VERSION as WORKFORCE_TRANSPORT_CATALOG_VERSION,
)


@dataclass(frozen=True)
class SeedManifestEntry:
    domain: str
    seed_id: str
    source: str
    deterministic: bool


CATALOG_VERSION: Final[str] = "ref4-phase1c-seed-manifest-v1"

SEED_MANIFEST_ENTRIES: Final[tuple[SeedManifestEntry, ...]] = (
    SeedManifestEntry("core_immutable_catalogs", "seed_core_immutable_v1", "python_registry", True),
    SeedManifestEntry("legal_document_catalogs", "seed_legal_document_v1", "python_registry", True),
    SeedManifestEntry("reference_field_schema_registry", "seed_field_schema_v1", "python_registry", True),
    SeedManifestEntry("workforce_transport_catalogs", "seed_workforce_transport_v1", "python_registry", True),
    SeedManifestEntry("tenant_override_foundation", "seed_tenant_override_foundation_v1", "python_registry", True),
    SeedManifestEntry("rule_pack_foundation", "seed_rule_pack_foundation_v1", "python_registry", True),
)

REFERENCE_VERSION_MANIFEST: Final[dict[str, str]] = {
    "core_immutable_catalogs": CORE_IMMUTABLE_CATALOG_VERSION,
    "legal_document_catalogs": LEGAL_DOCUMENT_CATALOG_VERSION,
    "reference_field_schema_registry": FIELD_SCHEMA_CATALOG_VERSION,
    "workforce_transport_catalogs": WORKFORCE_TRANSPORT_CATALOG_VERSION,
    "tenant_override_foundation": TENANT_OVERRIDE_FOUNDATION_CATALOG_VERSION,
    "rule_pack_foundation": RULE_PACK_FOUNDATION_CATALOG_VERSION,
}

MIGRATION_BOUNDARY_DESCRIPTION: Final[dict[str, str]] = {
    "phase_scope": "REF-4 Phase 1C foundation-only",
    "allowed": "manifest definition, deterministic checksum composition, migration boundary metadata",
    "blocked": "alembic migration execution, db write, seed runner, runtime sync, consumer rollout",
}


def list_seed_manifest_entries() -> tuple[SeedManifestEntry, ...]:
    return SEED_MANIFEST_ENTRIES


def get_reference_version_manifest() -> dict[str, str]:
    return dict(REFERENCE_VERSION_MANIFEST)


def compose_deterministic_seed_checksum() -> str:
    payload = {
        "catalog_version": CATALOG_VERSION,
        "entries": [
            {
                "domain": item.domain,
                "seed_id": item.seed_id,
                "source": item.source,
                "deterministic": bool(item.deterministic),
            }
            for item in SEED_MANIFEST_ENTRIES
        ],
        "reference_versions": REFERENCE_VERSION_MANIFEST,
        "migration_boundary": MIGRATION_BOUNDARY_DESCRIPTION,
    }
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _assert_manifest_integrity() -> None:
    domains = [item.domain for item in SEED_MANIFEST_ENTRIES]
    seed_ids = [item.seed_id for item in SEED_MANIFEST_ENTRIES]
    assert len(domains) == len(set(domains)), "Duplicate seed manifest domain"
    assert len(seed_ids) == len(set(seed_ids)), "Duplicate seed manifest seed_id"
    assert set(domains) == set(REFERENCE_VERSION_MANIFEST.keys()), "Manifest domains and version manifest mismatch"


_assert_manifest_integrity()


__all__ = [
    "CATALOG_VERSION",
    "SeedManifestEntry",
    "SEED_MANIFEST_ENTRIES",
    "REFERENCE_VERSION_MANIFEST",
    "MIGRATION_BOUNDARY_DESCRIPTION",
    "list_seed_manifest_entries",
    "get_reference_version_manifest",
    "compose_deterministic_seed_checksum",
]
