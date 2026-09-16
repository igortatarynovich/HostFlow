#!/usr/bin/env python3
"""PMI-0 fact map: deterministic owner|UNASSIGNED + reproducible cross-owner edge set.

Does not claim ISOLATED. Does not whitelist 'probably public' imports.
See docs/specs/tasks/platform-modularization-isolation-cutover.md.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OWNERS_PATH = REPO_ROOT / "scripts" / "architecture" / "module_isolation_owners.json"
BASELINE_PATH = REPO_ROOT / "scripts" / "architecture" / "module_isolation_pmi0_baseline.json"
SPINE_OWNERS = ("recruitment", "boundary", "employment", "documents", "workforce")


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def prefix_pairs(config: dict) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for owner, spec in (config.get("owners") or {}).items():
        for prefix in spec.get("prefixes") or []:
            pairs.append((prefix.rstrip("/"), str(owner)))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def matching_owners(rel_path: str, prefixes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for prefix, owner in prefixes:
        if rel_path == prefix:
            hits.append((prefix, owner))
            continue
        if rel_path.startswith(prefix + "/") or rel_path.startswith(prefix + "."):
            hits.append((prefix, owner))
            continue
        if prefix.endswith("_") and rel_path.startswith(prefix):
            hits.append((prefix, owner))
    return hits


def assign_owner(rel_path: str, prefixes: list[tuple[str, str]]) -> tuple[str, str | None]:
    hits = matching_owners(rel_path, prefixes)
    if not hits:
        return "UNASSIGNED", None
    max_len = max(len(p) for p, _ in hits)
    top = [(p, o) for p, o in hits if len(p) == max_len]
    owners = {o for _, o in top}
    if len(owners) != 1:
        raise RuntimeError(f"ambiguous owner for {rel_path}: {sorted(owners)} prefixes={[p for p, _ in top]}")
    return next(iter(owners)), top[0][0]


def iter_backend_py() -> list[Path]:
    app = REPO_ROOT / "backend" / "app"
    out: list[Path] = []
    for path in app.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        out.append(path)
    return sorted(out)


def imported_backend_modules(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("backend.app.") or name.startswith("app."):
                    found.add(name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if mod.startswith("backend.app") or mod.startswith("app."):
                found.add(mod)
    return found


def file_for_backend_module(mod: str) -> str | None:
    if mod.startswith("backend."):
        parts = mod.split(".")
    elif mod.startswith("app."):
        parts = ["backend", *mod.split(".")]
    else:
        return None
    base = REPO_ROOT.joinpath(*parts)
    py = base.with_suffix(".py")
    init = base / "__init__.py"
    if py.is_file():
        return rel(py)
    if init.is_file():
        return rel(init)
    return None


def prefix_matches_any(prefix: str, files: list[str]) -> bool:
    p = prefix.rstrip("/")
    for f in files:
        if f == p or f.startswith(p + "/") or f.startswith(p + "."):
            return True
        if p.endswith("_") and f.startswith(p):
            return True
    return False


def build_report(config: dict) -> dict:
    prefixes = prefix_pairs(config)
    files_by_owner: dict[str, list[str]] = defaultdict(list)
    assignment: dict[str, str] = {}
    backend_files = [rel(p) for p in iter_backend_py()]
    for rel_path in backend_files:
        owner, _matched = assign_owner(rel_path, prefixes)
        assignment[rel_path] = owner
        files_by_owner[owner].append(rel_path)

    edges: list[dict[str, str]] = []
    for rel_path in backend_files:
        path = REPO_ROOT / rel_path
        src_owner = assignment[rel_path]
        for mod in sorted(imported_backend_modules(path)):
            target = file_for_backend_module(mod)
            if not target or target not in assignment:
                continue
            dst_owner = assignment[target]
            if dst_owner == src_owner:
                continue
            edges.append(
                {
                    "from_file": rel_path,
                    "from_owner": src_owner,
                    "to_file": target,
                    "to_owner": dst_owner,
                    "import": mod,
                }
            )
    edges.sort(key=lambda e: (e["from_file"], e["import"], e["to_file"]))

    owners_declared = sorted((config.get("owners") or {}).keys())
    files_sorted = {k: sorted(v) for k, v in files_by_owner.items()}
    return {
        "schema": "pmi0.v1",
        "owners_declared": owners_declared,
        "spine_owners": list(SPINE_OWNERS),
        "backend_file_count": len(backend_files),
        "file_counts": {k: len(v) for k, v in sorted(files_sorted.items())},
        "files_by_owner": {k: files_sorted[k] for k in sorted(files_sorted)},
        "unassigned": files_sorted.get("UNASSIGNED", []),
        "unassigned_count": len(files_sorted.get("UNASSIGNED", [])),
        "cross_owner_edges": edges,
        "cross_owner_edge_count": len(edges),
    }


def validate_spine_roots(config: dict, report: dict) -> list[str]:
    errors: list[str] = []
    declared = set(report["owners_declared"])
    for name in SPINE_OWNERS:
        if name not in declared:
            errors.append(f"spine owner missing from owners map: {name}")
            continue
        files = report["files_by_owner"].get(name, [])
        if not files:
            errors.append(f"spine owner {name} matched 0 backend files")
        spec = (config.get("owners") or {}).get(name) or {}
        required = spec.get("required_prefixes") or []
        if not required:
            errors.append(f"spine owner {name} has empty required_prefixes")
        for prefix in required:
            if not prefix_matches_any(prefix, files):
                errors.append(f"spine owner {name} required prefix matched 0 files: {prefix}")
    classified = sum(report["file_counts"].values())
    if classified != report["backend_file_count"]:
        errors.append(
            f"classification incomplete: {classified} assigned vs {report['backend_file_count']} backend files"
        )
    unassigned = report["files_by_owner"].get("UNASSIGNED", [])
    if len(unassigned) != report["unassigned_count"]:
        errors.append("UNASSIGNED list/count mismatch")
    return errors


def canonical_baseline(report: dict) -> dict:
    return {
        "schema": report["schema"],
        "spine_owners": report["spine_owners"],
        "backend_file_count": report["backend_file_count"],
        "file_counts": report["file_counts"],
        "files_by_owner": report["files_by_owner"],
        "unassigned": report["unassigned"],
        "cross_owner_edges": report["cross_owner_edges"],
    }


def dump(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print summary JSON (not the full file lists)")
    parser.add_argument("--write", action="store_true", help="write committed PMI-0 baseline")
    parser.add_argument("--check", action="store_true", help="require baseline to match scanner output")
    args = parser.parse_args(argv)

    if not OWNERS_PATH.is_file():
        print(f"missing owners map: {OWNERS_PATH}", file=sys.stderr)
        return 1
    config = load_config(OWNERS_PATH)
    try:
        report = build_report(config)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    errors = validate_spine_roots(config, report)
    if errors:
        print("PMI-0 completeness STOP:", file=sys.stderr)
        for item in errors:
            print(f"  {item}", file=sys.stderr)
        return 1

    baseline = canonical_baseline(report)
    if args.write:
        BASELINE_PATH.write_text(dump(baseline), encoding="utf-8")
        print(f"wrote {BASELINE_PATH.relative_to(REPO_ROOT)}")
    if args.check:
        if not BASELINE_PATH.is_file():
            print(f"missing baseline (run --write): {BASELINE_PATH}", file=sys.stderr)
            return 1
        existing = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        if existing != baseline:
            print(
                "PMI-0 baseline drift: scanner output != "
                "scripts/architecture/module_isolation_pmi0_baseline.json "
                "(re-run with --write in the PMI-0 slice only; PMI-1 freeze is a later slice)",
                file=sys.stderr,
            )
            return 1

    summary = {
        "backend_file_count": report["backend_file_count"],
        "file_counts": report["file_counts"],
        "unassigned_count": report["unassigned_count"],
        "cross_owner_edge_count": report["cross_owner_edge_count"],
        "spine_file_counts": {name: report["file_counts"].get(name, 0) for name in SPINE_OWNERS},
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("PMI-0 module isolation fact map")
        print(f"  backend_file_count: {summary['backend_file_count']}")
        print(f"  file_counts: {summary['file_counts']}")
        print(f"  spine_file_counts: {summary['spine_file_counts']}")
        print(f"  unassigned_count: {summary['unassigned_count']}")
        print(f"  cross_owner_edge_count: {summary['cross_owner_edge_count']}")
        print("  leak set = full cross_owner_edges (no manual public filter)")
        print("  (map only — not ISOLATED, not PMI-1 freeze)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
