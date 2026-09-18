#!/usr/bin/env python3
"""PMI-UI: forbid parallel primitives, cross-spine composition leaks, new decision reconstructors.

Shrink-only allowlist. New edges FORBIDDEN after PMI-UI PASS.
Does not require rewriting all HostFlow frontend — non-spine debt stays listed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = REPO_ROOT / "scripts" / "architecture" / "ui_primitive_authority.json"
ALLOWLIST_PATH = REPO_ROOT / "scripts" / "architecture" / "ui_isolation_allowlist.txt"
FE_SRC = REPO_ROOT / "hostflow-frontend" / "src"

IMPORT_RE = re.compile(
    r"""(?:from|import)\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def load_auth() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def load_allowlist(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        # Full edge id: kind|from_file|detail (do not strip kind).
        out.add(s)
    return out


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def resolve_import(from_file: Path, spec: str) -> Path | None:
    if not spec.startswith("."):
        return None
    base = from_file.parent
    cand = (base / spec).resolve()
    for suffix in ("", ".ts", ".tsx", "/index.ts", "/index.tsx"):
        p = Path(str(cand) + suffix) if suffix.startswith(".") or suffix == "" else Path(str(cand) + suffix)
        if suffix == "":
            if cand.with_suffix(".ts").exists():
                return cand.with_suffix(".ts")
            if cand.with_suffix(".tsx").exists():
                return cand.with_suffix(".tsx")
            if (cand / "index.ts").exists():
                return cand / "index.ts"
            if (cand / "index.tsx").exists():
                return cand / "index.tsx"
            continue
        if p.exists():
            return p
    # try as file without knowing extension
    if cand.exists():
        return cand
    return None


def iter_fe_files() -> list[Path]:
    out: list[Path] = []
    for path in FE_SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if "node_modules" in path.parts or "__tests__" in path.parts or ".test." in path.name:
            continue
        out.append(path)
    return out


def under_prefix(path_rel: str, prefix: str) -> bool:
    return path_rel == prefix.rstrip("/") or path_rel.startswith(prefix)


def spine_owner(path_rel: str, spine_roots: dict[str, list[str]]) -> str | None:
    # more specific prefixes win (longest match)
    best: tuple[int, str] | None = None
    for owner, prefixes in spine_roots.items():
        for p in prefixes:
            if under_prefix(path_rel, p):
                score = len(p)
                if best is None or score > best[0]:
                    best = (score, owner)
    return best[1] if best else None


def edge_id(kind: str, from_file: str, detail: str) -> str:
    return f"{kind}|{from_file}|{detail}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-allowlist", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    auth = load_auth()
    forbidden_files = set()
    for cat in auth["categories"].values():
        for p in cat.get("forbidden_parallel", []):
            forbidden_files.add(p.replace("\\", "/"))

    recon_re = re.compile(auth["forbidden_new_reconstruction_basename_re"])
    legacy_recon = {p.replace("\\", "/") for p in auth.get("decision_reconstruction_legacy", [])}
    decision_ok = {p.replace("\\", "/") for p in auth.get("decision_display_ok", [])}
    spine_roots = auth["spine_roots"]

    violations: list[str] = []

    # 1) Imports of forbidden parallel primitives
    for path in iter_fe_files():
        from_rel = rel(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        for spec in IMPORT_RE.findall(text):
            target = resolve_import(path, spec)
            if not target:
                # also catch absolute-ish alias paths written as relative chains
                continue
            try:
                to_rel = rel(target)
            except ValueError:
                continue
            if to_rel in forbidden_files:
                violations.append(edge_id("parallel_import", from_rel, to_rel))

    # 2) Cross-spine composition: documents must not import recruitment/candidate internals
    for path in iter_fe_files():
        from_rel = rel(path)
        owner = spine_owner(from_rel, spine_roots)
        if owner != "documents":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for spec in IMPORT_RE.findall(text):
            target = resolve_import(path, spec)
            if not target:
                continue
            try:
                to_rel = rel(target)
            except ValueError:
                continue
            if "platform/design-system" in to_rel:
                continue
            to_owner = spine_owner(to_rel, spine_roots)
            if to_owner and to_owner != "documents" and to_owner != "employment":
                # documents → recruitment/candidate/boundary internals
                if to_owner in {"recruitment", "boundary", "workforce"}:
                    violations.append(edge_id("cross_spine", from_rel, f"{to_owner}:{to_rel}"))

    # 3) New decision reconstructors (basename match) outside legacy allow + display_ok
    for path in iter_fe_files():
        from_rel = rel(path)
        stem = path.stem
        if not recon_re.match(stem):
            continue
        if from_rel in legacy_recon or from_rel in decision_ok:
            # legacy listed separately as debt rows
            if from_rel in legacy_recon:
                violations.append(edge_id("decision_legacy", from_rel, stem))
            continue
        violations.append(edge_id("decision_new", from_rel, stem))

    # 4) Spine must not import candidate NextActionBadge shim when design-system exists
    #    (shim itself is allowed; foreign spine composers should use design-system)
    shim = "hostflow-frontend/src/components/candidate/NextActionBadge.tsx"
    for path in iter_fe_files():
        from_rel = rel(path)
        if from_rel == shim:
            continue
        owner = spine_owner(from_rel, spine_roots)
        if owner not in {"documents", "employment", "workforce", "boundary"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for spec in IMPORT_RE.findall(text):
            target = resolve_import(path, spec)
            if not target:
                continue
            try:
                to_rel = rel(target)
            except ValueError:
                continue
            if to_rel == shim:
                violations.append(edge_id("legacy_action_badge", from_rel, to_rel))

    ids = sorted(set(violations))

    if args.write_allowlist:
        lines = [
            "# PMI-UI UI isolation allowlist (shrink-only).",
            "# Format: kind|from_file|detail",
            "# New rows FORBIDDEN after PMI-UI PASS.",
            "# Scope: spine surfaces; remaining HostFlow UI may stay listed as debt.",
        ]
        lines.extend(ids)
        ALLOWLIST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {ALLOWLIST_PATH.relative_to(REPO_ROOT)} ({len(ids)} edges)")
        return 0

    allow = load_allowlist(ALLOWLIST_PATH)
    new_ids = [i for i in ids if i not in allow]
    grown = [i for i in allow if i not in ids]  # informational shrink candidates
    summary = {
        "violation_count": len(ids),
        "allowlist_count": len(allow),
        "new_violation_count": len(new_ids),
        "new_violations_sample": new_ids[:20],
        "allowlist_stale_count": len(grown),
        "ok": len(new_ids) == 0 and (len(ids) <= len(allow) if allow else len(new_ids) == 0),
        "authority": str(AUTH_PATH.relative_to(REPO_ROOT)),
        "public_surface": "hostflow-frontend/src/platform/design-system",
    }
    # shrink-only: allowlist may not grow; current violations must be ⊆ allowlist
    if allow and len(ids) > len(allow):
        summary["ok"] = False
    if new_ids:
        summary["ok"] = False

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"ui isolation: violations={len(ids)} allowlist={len(allow)} "
            f"new={len(new_ids)} ok={summary['ok']}"
        )
        for i in new_ids[:30]:
            print(f"  NEW {i}")

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
