#!/usr/bin/env python3
"""ADR-036 Phase 3 guard: no *new* job-title Role.* outside shim / grandfathered surfaces.

Shim allowlist (aliases + require_roles bridges until inventory rows are removed):
  backend/app/auth/**
  backend/app/api/v1/tenants/service.py
  backend/app/api/v1/platform/schemas.py
  backend/app/schemas/user.py
  backend/app/models/user.py

Grandfathered: existing backend/app/api and backend/app/modules trees (tracked in
rbac-role-usage-inventory.csv). This script fails only when a *new* path under
backend/app that is NOT in the baseline CSV introduces Role.<job_title>.

Usage:
  python scripts/rbac/check_no_new_job_title_roles.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "scripts" / "rbac" / "role_usage_inventory.csv"

FORBIDDEN = re.compile(
    r"Role\.(recruiter|supervisor|client_manager|client_processor|compliance_officer|hr_officer)\b"
)

SHIM_PREFIXES = (
    "backend/app/auth/",
    "backend/app/api/v1/tenants/service.py",
    "backend/app/api/v1/platform/schemas.py",
    "backend/app/api/v1/platform/tenants.py",
    "backend/app/api/v1/settings/team.py",
    "backend/app/schemas/user.py",
    "backend/app/models/user.py",
    "backend/app/constants/roles.py",
    "scripts/rbac/",
    "backend/tests/",
)


def _baseline_paths() -> set[str]:
    paths: set[str] = set()
    if not CSV_PATH.exists():
        return paths
    with CSV_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = (row.get("path") or "").split(":")[0]
            if p:
                paths.add(p)
    return paths


def _is_shim(rel: str) -> bool:
    return any(rel.startswith(p) or p in rel for p in SHIM_PREFIXES)


def main() -> int:
    baseline = _baseline_paths()
    violations: list[str] = []
    for path in (ROOT / "backend" / "app").rglob("*.py"):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if _is_shim(rel):
            continue
        # Only flag files not already in inventory baseline (new surfaces)
        if rel in baseline or any(rel.startswith(b.split(":")[0]) for b in baseline):
            # still in inventory — migration debt, not a lint fail
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN.search(line):
                violations.append(f"{rel}:{i}:{line.strip()}")

    print(f"rbac-role-lint: baseline_paths={len(baseline)} new_violations={len(violations)}")
    for v in violations[:40]:
        print(v)
    if violations:
        print(
            "ADR-036: new file introduces Role.<job_title>. "
            "Use employee/viewer + permissions/presets, or Architecture RFC.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
