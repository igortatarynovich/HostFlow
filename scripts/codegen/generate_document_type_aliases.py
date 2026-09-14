#!/usr/bin/env python3
"""Generate frontend document type alias projections from platform JSON SSOT."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALIASES_JSON = _REPO_ROOT / "docs" / "specs" / "platform" / "document-type-legacy-aliases-v1.json"
_REGISTRY_JSON = _REPO_ROOT / "docs" / "specs" / "platform" / "document-type-registry-v1.json"
_OUTPUT_TS = _REPO_ROOT / "hostflow-frontend" / "src" / "data" / "documentTypeAliases.ts"


def _norm(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _canonical_codes(registry_payload: dict) -> set[str]:
    return {_norm(item["code"]) for item in registry_payload.get("document_types") or []}


def build_alias_map() -> dict[str, str]:
    aliases_payload = _load_json(_ALIASES_JSON)
    registry_payload = _load_json(_REGISTRY_JSON)
    canonical = _canonical_codes(registry_payload)
    out: dict[str, str] = {}
    module_persist = {
        _norm(legacy): _norm(target)
        for legacy, target in (aliases_payload.get("module_persist_aliases") or {}).items()
        if _norm(legacy) and _norm(target)
    }

    for legacy, target in (aliases_payload.get("aliases") or {}).items():
        key = _norm(legacy)
        value = _norm(target)
        if key in module_persist:
            continue
        if value in canonical and key != value:
            out[key] = value

    for deprecated, replacement in (aliases_payload.get("deprecated_canonical_codes") or {}).items():
        key = _norm(deprecated)
        value = _norm(replacement)
        if key in module_persist:
            continue
        if value in canonical and key != value:
            out[key] = value

    for code in sorted(canonical):
        out.setdefault(code, code)

    return dict(sorted(out.items()))


def build_module_persist_aliases() -> dict[str, str]:
    aliases_payload = _load_json(_ALIASES_JSON)
    out: dict[str, str] = {}
    for legacy, target in (aliases_payload.get("module_persist_aliases") or {}).items():
        key = _norm(legacy)
        value = _norm(target)
        if key and value:
            out[key] = value
    return dict(sorted(out.items()))


def build_module_slot_satisfaction() -> dict[str, list[str]]:
    aliases_payload = _load_json(_ALIASES_JSON)
    out: dict[str, list[str]] = {}
    raw = aliases_payload.get("module_slot_satisfaction") or {}
    if not isinstance(raw, dict):
        return out
    for stored, slots in raw.items():
        key = _norm(stored)
        if not key or not isinstance(slots, list):
            continue
        values = [_norm(item) for item in slots if _norm(item)]
        if values:
            out[key] = list(dict.fromkeys(values))
    return dict(sorted(out.items()))


def build_equivalent_groups(alias_map: dict[str, str]) -> list[list[str]]:
    by_canonical: dict[str, set[str]] = defaultdict(set)
    for legacy, canonical in alias_map.items():
        by_canonical[canonical].add(legacy)
        by_canonical[canonical].add(canonical)
    groups = [sorted(codes) for codes in by_canonical.values() if len(codes) > 1]
    groups.sort(key=lambda group: group[0])
    return groups


def render_ts(
    alias_map: dict[str, str],
    groups: list[list[str]],
    module_persist: dict[str, str],
    slot_satisfaction: dict[str, list[str]],
) -> str:
    alias_lines = ",\n".join(f'  "{k}": "{v}"' for k, v in alias_map.items())
    group_lines = ",\n".join("  [" + ", ".join(f'"{code}"' for code in group) + "]" for group in groups)
    persist_lines = ",\n".join(f'  "{k}": "{v}"' for k, v in module_persist.items())
    slot_lines = ",\n".join(
        '  "{k}": [{items}]'.format(
            k=k,
            items=", ".join(f'"{code}"' for code in values),
        )
        for k, values in slot_satisfaction.items()
    )
    return f"""/**
 * Generated from docs/specs/platform/document-type-legacy-aliases-v1.json.
 * Regenerate: python3 scripts/codegen/generate_document_type_aliases.py
 */
export const DOC_TYPE_LEGACY_ALIASES: Record<string, string> = {{
{alias_lines}
}};

export const MODULE_PERSIST_DOC_TYPE_ALIASES: Record<string, string> = {{
{persist_lines}
}};

export const COMBINED_LICENSE_SATISFIES: Record<string, string[]> = {{
{slot_lines}
}};

export const EQUIVALENT_TYPE_GROUPS: string[][] = [
{group_lines}
];
"""


def generate() -> str:
    alias_map = build_alias_map()
    groups = build_equivalent_groups(alias_map)
    module_persist = build_module_persist_aliases()
    slot_satisfaction = build_module_slot_satisfaction()
    return render_ts(alias_map, groups, module_persist, slot_satisfaction)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated file drifts")
    args = parser.parse_args()

    content = generate()
    if args.check:
        if not _OUTPUT_TS.exists():
            print(f"missing generated file: {_OUTPUT_TS}", file=sys.stderr)
            return 1
        if _OUTPUT_TS.read_text(encoding="utf-8") != content:
            print(
                "document type alias codegen drift; run:\n"
                "  python3 scripts/codegen/generate_document_type_aliases.py",
                file=sys.stderr,
            )
            return 1
        print("codegen check: document_type_aliases OK")
        return 0

    _OUTPUT_TS.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_TS.write_text(content, encoding="utf-8")
    print(f"wrote {_OUTPUT_TS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
