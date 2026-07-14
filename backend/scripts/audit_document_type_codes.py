#!/usr/bin/env python3
"""
ADR-018 Phase 1 — audit all document type codes across registry, code, and DB.

Usage (repo root):

    python3 backend/scripts/audit_document_type_codes.py
    python3 backend/scripts/audit_document_type_codes.py --json report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "hostflow-frontend"

_SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".json", ".md"}
_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
}

_DOC_TYPE_LITERAL_RE = re.compile(
    r"""(?:doc_type|document_type|type)\s*[:=]\s*['"]([a-z][a-z0-9_]{1,63})['"]""",
    re.IGNORECASE,
)
_JSON_CODE_RE = re.compile(r"""['"]code['"]\s*:\s*['"]([a-z][a-z0-9_]{1,63})['"]""")
_MODULE_CATALOG_RE = re.compile(r"""code\s*=\s*['"]([a-z][a-z0-9_]{1,63})['"]""")


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(BACKEND_ROOT.parent if (BACKEND_ROOT.parent / "backend").exists() else REPO_ROOT))


def _iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in _SCAN_EXTENSIONS:
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _scan_file(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    found: set[str] = set()
    for pattern in (_DOC_TYPE_LITERAL_RE, _JSON_CODE_RE):
        for match in pattern.finditer(text):
            found.add(match.group(1).lower())
    if path.name == "definitions.py":
        for match in _MODULE_CATALOG_RE.finditer(text):
            if "DocumentTypeDefinition" in text:
                found.add(match.group(1).lower())
    return found


def _load_registry_context() -> dict:
    from backend.app.document_types.registry import (
        build_legacy_to_canonical_map,
        canonical_codes,
        driver_ce_canonical_codes,
        normalize_input_doc_type,
        registry_version,
    )

    mapping = build_legacy_to_canonical_map()
    return {
        "registry_version": registry_version(),
        "canonical_codes": sorted(canonical_codes()),
        "driver_ce_codes": sorted(driver_ce_canonical_codes()),
        "legacy_map_size": len(mapping),
        "normalize_input_doc_type": normalize_input_doc_type,
        "mapping": mapping,
        "canonical_set": set(canonical_codes()),
    }


def _scan_codebase() -> dict[str, set[str]]:
    by_file: dict[str, set[str]] = {}
    for root in (BACKEND_ROOT, FRONTEND_ROOT, REPO_ROOT / "docs" / "specs"):
        if not root.exists():
            continue
        for path in _iter_source_files(root):
            codes = _scan_file(path)
            if codes:
                by_file[str(path.relative_to(REPO_ROOT))] = codes
    return by_file


def _classify_codes(found: set[str], ctx: dict) -> dict[str, list[str]]:
    canonical = ctx["canonical_set"]
    mapping = ctx["mapping"]
    normalize = ctx["normalize_input_doc_type"]

    known_canonical: list[str] = []
    known_legacy: list[str] = []
    unknown: list[str] = []
    ambiguous: list[str] = []

    for code in sorted(found):
        if code in canonical:
            known_canonical.append(code)
            continue
        if code in mapping:
            target = mapping[code]
            if target != code:
                known_legacy.append(code)
            else:
                known_canonical.append(code)
            continue
        normalized = normalize(code)
        if normalized == "other" and code != "other":
            unknown.append(code)
        elif normalized in canonical:
            known_legacy.append(code)
        else:
            unknown.append(code)

    # ambiguous: legacy strings mapping to same canonical from multiple sources
    reverse: dict[str, set[str]] = defaultdict(set)
    for legacy, target in mapping.items():
        reverse[target].add(legacy)
    for target, legacies in reverse.items():
        module_hits = {c for c in legacies if c in found}
        if len(module_hits) > 3 and target in {"driver_license", "unclassified"}:
            ambiguous.extend(sorted(module_hits))

    return {
        "known_canonical": known_canonical,
        "known_legacy": known_legacy,
        "unknown": sorted(set(unknown)),
        "ambiguous": sorted(set(ambiguous)),
    }


def _scan_database_doc_types() -> dict | None:
    try:
        from sqlalchemy import create_engine, text

        from backend.app.core.config import settings
    except Exception as exc:  # pragma: no cover - optional when no DB
        return {"available": False, "reason": str(exc)}

    url = getattr(settings, "DATABASE_URL", None) or getattr(settings, "SQLALCHEMY_DATABASE_URI", None)
    if not url:
        return {"available": False, "reason": "DATABASE_URL not configured"}

    sync_url = str(url).replace("+asyncpg", "").replace("+aiosqlite", "")
    try:
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT lower(doc_type) AS doc_type, count(*) AS cnt
                    FROM documents
                    GROUP BY lower(doc_type)
                    ORDER BY cnt DESC
                    """
                )
            ).mappings().all()
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    return {
        "available": True,
        "counts": {str(row["doc_type"]): int(row["cnt"]) for row in rows},
    }


def build_report() -> dict:
    _bootstrap_imports()
    ctx = _load_registry_context()
    by_file = _scan_codebase()
    all_codes: set[str] = set()
    for codes in by_file.values():
        all_codes |= codes

    classification = _classify_codes(all_codes, ctx)
    db = _scan_database_doc_types()

    db_unknown: list[dict] = []
    if db and db.get("available"):
        normalize = ctx["normalize_input_doc_type"]
        for doc_type, count in db.get("counts", {}).items():
            canonical = normalize(doc_type)
            if canonical == "other" and doc_type not in ctx["canonical_set"] and doc_type != "other":
                db_unknown.append({"doc_type": doc_type, "count": count, "normalized_to": canonical})

    return {
        "registry_version": ctx["registry_version"],
        "canonical_code_count": len(ctx["canonical_codes"]),
        "driver_ce_code_count": len(ctx["driver_ce_codes"]),
        "files_scanned": len(by_file),
        "unique_codes_found": len(all_codes),
        "classification": classification,
        "database": db,
        "database_unknown_doc_types": db_unknown,
        "top_file_hits": Counter(
            {path: len(codes) for path, codes in by_file.items()}
        ).most_common(15),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit document type codes (ADR-018 Phase 1)")
    parser.add_argument("--json", dest="json_path", help="Write full JSON report to path")
    args = parser.parse_args()

    report = build_report()
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    classification = report["classification"]
    print(f"Registry version: {report['registry_version']}")
    print(f"Canonical codes: {report['canonical_code_count']} | Driver CE: {report['driver_ce_code_count']}")
    print(f"Scanned files: {report['files_scanned']} | Unique codes found: {report['unique_codes_found']}")
    print(f"Known canonical: {len(classification['known_canonical'])}")
    print(f"Known legacy (mapped): {len(classification['known_legacy'])}")
    print(f"Unknown: {len(classification['unknown'])}")
    if classification["unknown"]:
        print("Unknown codes:")
        for code in classification["unknown"][:50]:
            print(f"  - {code}")
    if report.get("database_unknown_doc_types"):
        print("Unknown DB doc_type values:")
        for row in report["database_unknown_doc_types"][:20]:
            print(f"  - {row['doc_type']} ({row['count']} rows) -> {row['normalized_to']}")

    return 1 if report.get("database_unknown_doc_types") else 0


if __name__ == "__main__":
    raise SystemExit(main())
