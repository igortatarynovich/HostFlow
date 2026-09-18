#!/usr/bin/env python3
"""PMI-E: foreign modules may import Employment only via public contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_module_isolation_map import (  # noqa: E402
    OWNERS_PATH,
    assign_owner,
    file_for_backend_module,
    imported_backend_modules,
    load_config,
    prefix_pairs,
)

ALLOWLIST_PATH = REPO_ROOT / "scripts" / "architecture" / "employment_isolation_allowlist.txt"
PUBLIC_PREFIX = "backend/app/modules/employment/public"
FOREIGN_OWNERS = {
    "recruitment",
    "boundary",
    "documents",
    "workforce",
    "platform",
    "integrations",
    "communications",
    "acquisition",
    "sales",
    "forms",
}


def load_allowlist(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if "|" in s:
            _, rel = s.split("|", 1)
            out.add(rel.strip())
        else:
            out.add(s)
    return out


def edge_id(from_file: str, import_mod: str, to_file: str) -> str:
    return f"{from_file}::{import_mod}::{to_file}"


def is_public(to_file: str, import_mod: str) -> bool:
    if to_file == PUBLIC_PREFIX or to_file.startswith(PUBLIC_PREFIX + "/"):
        return True
    if "modules.employment.public" in import_mod:
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-allowlist", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(OWNERS_PATH)
    prefixes = prefix_pairs(config)
    violations: list[tuple[str, str, str, str]] = []

    for path in sorted((REPO_ROOT / "backend" / "app").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        fo, _ = assign_owner(rel, prefixes)
        if fo not in FOREIGN_OWNERS:
            continue
        for mod in sorted(imported_backend_modules(path)):
            target = file_for_backend_module(mod)
            if not target:
                continue
            to, _ = assign_owner(target, prefixes)
            if to != "employment":
                continue
            if is_public(target, mod):
                continue
            violations.append((fo, rel, mod, target))

    ids = sorted({edge_id(a, b, c) for _, a, b, c in violations})

    if args.write_allowlist:
        lines = [
            "# PMI-E employment isolation allowlist (shrink-only).",
            "# Format: owner|from_file::import::to_file",
            "# New rows FORBIDDEN after PMI-E PASS.",
            "# EXC-PMI-B-DOC (Boundary→Documents) stays until PMI-D — not this allowlist.",
        ]
        for fo, a, b, c in sorted(violations, key=lambda x: (x[0], x[1], x[2])):
            lines.append(f"{fo}|{edge_id(a, b, c)}")
        ALLOWLIST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {ALLOWLIST_PATH.relative_to(REPO_ROOT)} ({len(ids)} edges)")
        return 0

    allow = load_allowlist(ALLOWLIST_PATH)
    allow_ids = {x.split("|", 1)[-1] if "|" in x else x for x in allow}
    new_ids = [i for i in ids if i not in allow_ids]
    summary = {
        "violation_count": len(ids),
        "allowlist_count": len(allow_ids),
        "new_violation_count": len(new_ids),
        "new_violations_sample": new_ids[:20],
        "ok": len(new_ids) == 0,
    }
    if new_ids:
        print("PMI-E employment isolation STOP: new non-public Employment imports", file=sys.stderr)
        for item in new_ids[:30]:
            print(f"  {item}", file=sys.stderr)
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 1
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("PMI-E employment isolation")
        print(f"  foreign→employment non-public (allowlisted): {len(ids)}")
        print("  new violations: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
