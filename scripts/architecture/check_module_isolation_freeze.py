#!/usr/bin/env python3
"""PMI-1 enforcement freeze: debt may only shrink; new cross-owner edges FAIL.

Authority: scripts/architecture/module_isolation_pmi0_baseline.json @ 844900d6
Does not remediate leaks. Does not open Ready/Kernel. See
docs/specs/tasks/platform-modularization-isolation-cutover.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_module_isolation_map import (  # noqa: E402
    BASELINE_PATH,
    OWNERS_PATH,
    build_report,
    file_for_backend_module,
    imported_backend_modules,
    load_config,
    validate_spine_roots,
)

FREEZE_PATH = REPO_ROOT / "scripts" / "architecture" / "module_isolation_pmi1_freeze.json"
DEBT_PATH = REPO_ROOT / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"


def edge_key(edge: dict) -> tuple[str, str, str]:
    return (edge["from_file"], edge["import"], edge["to_file"])


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structural_set(edges: list[dict]) -> set[tuple[str, str, str]]:
    return {edge_key(e) for e in edges}


def import_still_present(from_file: str, import_mod: str, to_file: str) -> bool:
    path = REPO_ROOT / from_file
    if not path.is_file():
        return False
    mods = imported_backend_modules(path)
    if import_mod not in mods:
        return False
    resolved = file_for_backend_module(import_mod)
    return resolved == to_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--shrink-debt",
        action="store_true",
        help="rewrite debt to current∩debt (only after gate is green)",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []

    if not FREEZE_PATH.is_file():
        print(f"missing freeze lock: {FREEZE_PATH}", file=sys.stderr)
        return 1
    freeze = load_json(FREEZE_PATH)
    if freeze.get("schema") != "pmi1.v1":
        errors.append(f"unexpected freeze schema: {freeze.get('schema')}")
    if freeze.get("authority_commit") != "844900d6":
        errors.append(
            f"authority_commit must be 844900d6, got {freeze.get('authority_commit')}"
        )

    if not BASELINE_PATH.is_file():
        print(f"missing authority baseline: {BASELINE_PATH}", file=sys.stderr)
        return 1
    actual_sha = sha256_file(BASELINE_PATH)
    expected_sha = freeze.get("authority_sha256")
    if actual_sha != expected_sha:
        errors.append(
            "authority baseline mutated (PMI-0 baseline is immutable after freeze); "
            f"expected sha256 {expected_sha}, got {actual_sha}"
        )

    authority = load_json(BASELINE_PATH)
    authority_edges = structural_set(authority.get("cross_owner_edges") or [])
    if len(authority_edges) != freeze.get("authority_edge_count"):
        errors.append(
            f"authority edge count mismatch: freeze={freeze.get('authority_edge_count')} "
            f"file={len(authority_edges)}"
        )

    if not DEBT_PATH.is_file():
        print(f"missing debt allowlist: {DEBT_PATH}", file=sys.stderr)
        return 1
    debt_doc = load_json(DEBT_PATH)
    debt_edges = structural_set(debt_doc.get("edges") or [])

    debt_growth = debt_edges - authority_edges
    if debt_growth:
        sample = sorted(debt_growth)[:10]
        errors.append(
            f"debt growth vs authority FORBIDDEN ({len(debt_growth)} new keys); "
            f"sample={sample}"
        )

    removed = authority_edges - debt_edges
    fake_shrink: list[tuple[str, str, str]] = []
    for key in sorted(removed):
        if import_still_present(*key):
            fake_shrink.append(key)
    if fake_shrink:
        errors.append(
            f"debt shrink while import still present FORBIDDEN ({len(fake_shrink)}); "
            f"sample={fake_shrink[:10]}"
        )

    if not OWNERS_PATH.is_file():
        print(f"missing owners map: {OWNERS_PATH}", file=sys.stderr)
        return 1
    config = load_config(OWNERS_PATH)
    try:
        report = build_report(config)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    map_errors = validate_spine_roots(config, report)
    if map_errors:
        errors.extend(f"map: {m}" for m in map_errors)

    current_edges = structural_set(report.get("cross_owner_edges") or [])
    new_leaks = current_edges - debt_edges
    if new_leaks:
        sample = sorted(new_leaks)[:15]
        errors.append(
            f"new cross-owner edge vs debt FORBIDDEN ({len(new_leaks)}); sample={sample}"
        )

    hidden: list[tuple[str, str, str]] = []
    for key in sorted(debt_edges):
        if import_still_present(*key) and key not in current_edges:
            hidden.append(key)
    if hidden:
        errors.append(
            f"ownership/prefix hide of debt edge FORBIDDEN ({len(hidden)}); "
            f"sample={hidden[:10]}"
        )

    if args.shrink_debt:
        if errors:
            print("refusing --shrink-debt while freeze gate is red:", file=sys.stderr)
            for item in errors:
                print(f"  {item}", file=sys.stderr)
            return 1
        kept = sorted(
            [
                {"from_file": a, "import": b, "to_file": c}
                for (a, b, c) in debt_edges
                if (a, b, c) in current_edges
            ],
            key=lambda e: (e["from_file"], e["import"], e["to_file"]),
        )
        out = {
            "schema": "pmi1.debt.v1",
            "authority_commit": "844900d6",
            "edges": kept,
        }
        DEBT_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"shrank debt {len(debt_edges)} → {len(kept)}")
        return 0

    summary = {
        "authority_edge_count": len(authority_edges),
        "debt_edge_count": len(debt_edges),
        "current_cross_owner_edge_count": len(current_edges),
        "new_leak_count": len(new_leaks),
        "hidden_count": len(hidden),
        "debt_growth_count": len(debt_growth),
        "fake_shrink_count": len(fake_shrink),
        "ok": not errors,
    }

    if errors:
        print("PMI-1 freeze STOP:", file=sys.stderr)
        for item in errors:
            print(f"  {item}", file=sys.stderr)
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("PMI-1 enforcement freeze")
        print(f"  authority_commit: {freeze['authority_commit']}")
        print(f"  authority_edges: {len(authority_edges)}")
        print(f"  debt_edges: {len(debt_edges)}")
        print(f"  current_cross_owner_edges: {len(current_edges)}")
        print("  invariant: debt may only shrink; new coupling rejected")
        print("  (ratchet only — not ISOLATED, not Ready/Kernel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
