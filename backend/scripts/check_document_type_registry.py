#!/usr/bin/env python3
"""
ADR-018 Phase 1 — merge-blocking guard for canonical Document Type Registry.

Fails when:
- module catalog ``definitions.py`` adds codes without registry binding;
- ``definitions.py`` canonical_ref_code points outside registry;
- deprecated legacy seed codes reappear in sync/packs;
- new hardcoded document type literals appear outside allowlist paths.

Usage (repo root):

    python3 backend/scripts/check_document_type_registry.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFINITIONS_FILE = BACKEND_ROOT / "app" / "document_types" / "definitions.py"
SYNC_FILE = BACKEND_ROOT / "app" / "services" / "document_reference_sync.py"

_FORBIDDEN_DEPRECATED_CODES = frozenset({"psychotest", "code_95", "id_card"})

_HARDCODED_SCAN_DIRS = (
    BACKEND_ROOT / "app" / "requirement_rules",
    BACKEND_ROOT / "app" / "modules" / "documents",
    BACKEND_ROOT / "app" / "services" / "candidate_doc_pipeline_guard.py",
)

_ALLOWED_LITERAL_PATHS = frozenset(
    {
        "backend/app/document_types/definitions.py",
        "backend/app/document_types/registry.py",
        "backend/app/services/document_type_canonical_bridge.py",
        "backend/app/services/document_reference_sync.py",
        "backend/app/requirement_rules/data/requirement_slots.v1.json",
        "docs/specs/platform/document-type-registry-v1.json",
        "docs/specs/platform/document-type-legacy-aliases-v1.json",
    }
)

_HARDCODED_DOC_TYPE_RE = re.compile(
    r"""(?:doc_type\s*=\s*['"]([a-z][a-z0-9_]{1,63})['"]|['"]doc_type['"]\s*:\s*['"]([a-z][a-z0-9_]{1,63})['"])""",
    re.IGNORECASE,
)


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(REPO_ROOT))


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _check_definitions_registry_bindings(errors: list[str]) -> None:
    from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS
    from backend.app.document_types.registry import canonical_codes, registry_entry_for

    canonical = canonical_codes()
    bindings = {
        str(item.get("module_code")).strip().lower()
        for item in __import__(
            "json"
        ).loads((REPO_ROOT / "docs/specs/platform/document-type-registry-v1.json").read_text())
        .get("module_catalog_bindings", [])
    }

    for definition in DOCUMENT_TYPE_DEFINITIONS:
        module_code = definition.code.strip().lower()
        ref = (definition.canonical_ref_code or "other").strip().lower()
        if ref not in canonical:
            errors.append(
                f"definitions.py: module code '{module_code}' canonical_ref_code '{ref}' not in registry"
            )
        if module_code not in bindings:
            errors.append(
                f"definitions.py: module code '{module_code}' missing from document-type-registry module_catalog_bindings"
            )
        entry = registry_entry_for(ref)
        if entry is None:
            errors.append(f"definitions.py: canonical_ref_code '{ref}' has no registry entry")


def _check_sync_deprecated_codes(errors: list[str]) -> None:
    text = SYNC_FILE.read_text(encoding="utf-8")
    for code in _FORBIDDEN_DEPRECATED_CODES:
        if f'"{code}"' in text or f"'{code}'" in text:
            errors.append(f"document_reference_sync.py: deprecated canonical code '{code}' must not be re-seeded")


def _check_hardcoded_literals(errors: list[str]) -> None:
    from backend.app.document_types.registry import build_legacy_to_canonical_map, canonical_codes

    allowed_values = canonical_codes() | frozenset(build_legacy_to_canonical_map().keys())
    skip_dirs = {"__pycache__", "node_modules", ".pytest_cache"}

    paths: list[Path] = []
    for item in _HARDCODED_SCAN_DIRS:
        if item.is_file():
            paths.append(item)
        elif item.is_dir():
            paths.extend(p for p in item.rglob("*") if p.is_file())

    for path in paths:
        if path.suffix not in {".py", ".json"}:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        rel = _rel(path)
        if rel in _ALLOWED_LITERAL_PATHS:
            continue
        if "test_" in path.name:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in _HARDCODED_DOC_TYPE_RE.finditer(text):
            value = (match.group(1) or match.group(2) or "").lower()
            if not value or value in allowed_values:
                continue
            errors.append(f"{rel}: hardcoded doc_type '{value}' outside registry allowlist")


def main() -> int:
    _bootstrap_imports()
    errors: list[str] = []
    _check_definitions_registry_bindings(errors)
    _check_sync_deprecated_codes(errors)
    _check_hardcoded_literals(errors)

    if errors:
        print("ADR-018 document type registry check FAILED:\n")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("ADR-018 document type registry check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
