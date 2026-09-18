#!/usr/bin/env python3
"""PMI-R: foreign modules may import Recruitment only via public contracts.

Named foreign owners importing Recruitment internals (non-public) must be on the
shrink-only exception allowlist. See docs/modules/recruitment/module_isolation_card.md.
"""

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

ALLOWLIST_PATH = (
    REPO_ROOT / "scripts" / "architecture" / "recruitment_isolation_boundary_allowlist.txt"
)
PUBLIC_PREFIX = "backend/app/modules/recruitment/public"
FOREIGN_OWNERS = {
    "boundary",
    "employment",
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
    if "modules.recruitment.public" in import_mod:
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-allowlist",
        action="store_true",
        help="write current violations as allowlist (PMI-R open only; later shrink-only)",
    )
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
            if to != "recruitment":
                continue
            if is_public(target, mod):
                continue
            violations.append((fo, rel, mod, target))

    ids = sorted({edge_id(a, b, c) for _, a, b, c in violations})

    if args.write_allowlist:
        lines = [
            "# PMI-R recruitment isolation allowlist (shrink-only).",
            "# Format: owner|from_file::import::to_file",
            "# New rows FORBIDDEN after PMI-R PASS.",
        ]
        for fo, a, b, c in sorted(violations, key=lambda x: (x[0], x[1], x[2])):
            lines.append(f"{fo}|{edge_id(a, b, c)}")
        ALLOWLIST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {ALLOWLIST_PATH.relative_to(REPO_ROOT)} ({len(ids)} edges)")
        return 0

    allow = load_allowlist(ALLOWLIST_PATH)
    # Allowlist stores full edge ids (optionally with owner| prefix stripped by loader).
    allow_ids = {x.split("|", 1)[-1] if "|" in x else x for x in allow}
    # Also accept entries that are the full "owner|id" stored without split confusion —
    # load_allowlist already strips owner|.

    new_ids = [i for i in ids if i not in allow_ids]
    # Growth of allowlist file vs committed set is checked by: new violations not in allow.
    # Shrinking allow is OK; adding allow rows without removing code is a process fail —
    # CI compares allow ⊆ previous only when --check-allowlist-shrink is used later.

    stale = sorted(allow_ids - set(ids))
    summary = {
        "violation_count": len(ids),
        "allowlist_count": len(allow_ids),
        "new_violation_count": len(new_ids),
        "stale_allowlist_count": len(stale),
        "new_violations_sample": new_ids[:20],
        "ok": len(new_ids) == 0,
    }

    if new_ids:
        print("PMI-R recruitment isolation STOP: new non-public Recruitment imports", file=sys.stderr)
        for item in new_ids[:30]:
            print(f"  {item}", file=sys.stderr)
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("PMI-R recruitment isolation")
        print(f"  foreign→recruitment non-public (allowlisted): {len(ids)}")
        print(f"  new violations: 0")
        print("  rule: named foreign owners → recruitment.public only (exceptions shrink-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
