"""Canonical Document Type Registry loader (ADR-018 SSOT).

Registry JSON is the single source of truth for stable document type codes.
Legacy aliases are permitted only for input normalization and migration — never
for Requirement Evaluation runtime matching.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_SPECS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "specs" / "platform"
REGISTRY_PATH = _SPECS_ROOT / "document-type-registry-v1.json"
LEGACY_ALIASES_PATH = _SPECS_ROOT / "document-type-legacy-aliases-v1.json"


def _norm(value: Optional[str]) -> str:
    return str(value or "").strip().lower().replace("-", "_")


@dataclass(frozen=True)
class DocumentTypeRegistryEntry:
    code: str
    public_name: str
    category_code: str
    subcategory_code: Optional[str]
    criticality: str
    driver_ce_contour: bool
    schema_version: str
    participates_in_requirements: bool
    business_purposes: tuple[str, ...]
    entity_applicability: tuple[str, ...]
    classification_inbox_only: bool = False


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_registry_payload() -> dict[str, Any]:
    return _load_json(REGISTRY_PATH)


@lru_cache(maxsize=1)
def load_legacy_aliases_payload() -> dict[str, Any]:
    return _load_json(LEGACY_ALIASES_PATH)


@lru_cache(maxsize=1)
def registry_entries() -> tuple[DocumentTypeRegistryEntry, ...]:
    payload = load_registry_payload()
    entries: list[DocumentTypeRegistryEntry] = []
    for raw in payload.get("document_types") or []:
        entries.append(
            DocumentTypeRegistryEntry(
                code=_norm(raw["code"]),
                public_name=str(raw.get("public_name") or raw["code"]),
                category_code=str(raw.get("category_code") or "other"),
                subcategory_code=_norm(raw["subcategory_code"]) if raw.get("subcategory_code") else None,
                criticality=str(raw.get("criticality") or "informational"),
                driver_ce_contour=bool(raw.get("driver_ce_contour")),
                schema_version=str(raw.get("schema_version") or "v1"),
                participates_in_requirements=bool(raw.get("participates_in_requirements", True)),
                business_purposes=tuple(str(x) for x in (raw.get("business_purposes") or [])),
                entity_applicability=tuple(str(x) for x in (raw.get("entity_applicability") or [])),
                classification_inbox_only=bool(raw.get("classification_inbox_only")),
            )
        )
    return tuple(entries)


@lru_cache(maxsize=1)
def canonical_codes() -> frozenset[str]:
    return frozenset(entry.code for entry in registry_entries())


@lru_cache(maxsize=1)
def driver_ce_canonical_codes() -> frozenset[str]:
    return frozenset(entry.code for entry in registry_entries() if entry.driver_ce_contour)


@lru_cache(maxsize=1)
def requirement_participating_codes() -> frozenset[str]:
    return frozenset(
        entry.code for entry in registry_entries() if entry.participates_in_requirements
    )


@lru_cache(maxsize=1)
def build_legacy_to_canonical_map() -> dict[str, str]:
    """All legacy/module strings → canonical code (input normalization only)."""
    out: dict[str, str] = {}

    for code in canonical_codes():
        out[code] = code

    payload = load_legacy_aliases_payload()
    for legacy, canonical in (payload.get("aliases") or {}).items():
        key = _norm(legacy)
        target = _norm(canonical)
        if target in canonical_codes():
            out[key] = target

    for deprecated, replacement in (payload.get("deprecated_canonical_codes") or {}).items():
        key = _norm(deprecated)
        target = _norm(replacement)
        if target in canonical_codes():
            out[key] = target

    for binding in load_registry_payload().get("module_catalog_bindings") or []:
        module_code = _norm(binding.get("module_code"))
        canonical = _norm(binding.get("canonical_code"))
        if module_code and canonical in canonical_codes():
            out[module_code] = canonical

    from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS

    for definition in DOCUMENT_TYPE_DEFINITIONS:
        module_code = _norm(definition.code)
        canonical = _norm(definition.canonical_ref_code or "")
        if canonical in canonical_codes():
            out[module_code] = canonical
        for alias in definition.aliases:
            alias_key = _norm(alias)
            if alias_key and canonical in canonical_codes():
                out[alias_key] = canonical

    for code in canonical_codes():
        out[code] = code

    return out


def normalize_input_doc_type(value: Optional[str]) -> str:
    """Map legacy/module doc_type to canonical registry code."""
    key = _norm(value)
    if not key:
        return "other"
    return build_legacy_to_canonical_map().get(key, "other")


def is_canonical_code(value: Optional[str]) -> bool:
    return _norm(value) in canonical_codes()


def is_runtime_alias(value: Optional[str]) -> bool:
    """True when value is a legacy alias, not a canonical code."""
    key = _norm(value)
    if not key or key in canonical_codes():
        return False
    return key in build_legacy_to_canonical_map()


def legacy_codes_for_canonical(canonical_code: str) -> frozenset[str]:
    target = _norm(canonical_code)
    return frozenset(k for k, v in build_legacy_to_canonical_map().items() if v == target)


def registry_entry_for(code: str) -> Optional[DocumentTypeRegistryEntry]:
    target = _norm(code)
    for entry in registry_entries():
        if entry.code == target:
            return entry
    return None


def registry_version() -> str:
    return str(load_registry_payload().get("registry_version") or "unknown")


__all__ = [
    "DocumentTypeRegistryEntry",
    "REGISTRY_PATH",
    "LEGACY_ALIASES_PATH",
    "build_legacy_to_canonical_map",
    "canonical_codes",
    "driver_ce_canonical_codes",
    "is_canonical_code",
    "is_runtime_alias",
    "legacy_codes_for_canonical",
    "load_legacy_aliases_payload",
    "load_registry_payload",
    "normalize_input_doc_type",
    "registry_entries",
    "registry_entry_for",
    "registry_version",
    "requirement_participating_codes",
]
