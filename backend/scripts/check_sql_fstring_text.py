#!/usr/bin/env python3
"""Fail CI if new dynamic SQL uses text(f\"...\") outside allowlisted files.

HostFlow rule: no f-string interpolation inside SQLAlchemy ``text()`` for runtime
queries (SQL injection + tenant bypass risk). Burn-down allowlist in
``ALLOWLIST_FILES`` — do not grow without security review.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "backend" / "app"

# Transitional allowlist — remove entries as code is refactored to bound parameters.
ALLOWLIST_FILES: frozenset[str] = frozenset(
    {
        "backend/app/auth/ensure_seed.py",
        "backend/app/models/lead_import_job.py",
    }
)

PATTERN = re.compile(r"\btext\s*\(\s*f[\"']")


def main() -> int:
    bad: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if PATTERN.search(text) is None:
            continue
        if rel in ALLOWLIST_FILES:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if PATTERN.search(line):
                bad.append(f"{rel}:{i}:{line.strip()[:120]}")

    if not bad:
        return 0

    print("Forbidden text(f'...') / text(f\"...\") SQL literals found:\n", file=sys.stderr)
    for b in bad:
        print(b, file=sys.stderr)
    print(
        "\nUse bound parameters / SQLAlchemy Core constructs instead. "
        "See docs/security/security-ssot.md (SQL / tenant enforcement).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
