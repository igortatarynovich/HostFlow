#!/usr/bin/env python3
"""
Merge gate: forbid raw ``emit_security_event(`` outside the allowlist.

- ``emit_security_event_v1(`` is always OK.
- ``def emit_security_event(`` (function definition) is ignored.
- Scans ``backend/app/**/*.py`` only (production producers).

Run from repo root::

    python3 scripts/security/check_no_raw_emit_security_event.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = REPO_ROOT / "backend" / "app"
ALLOWLIST_FILE = REPO_ROOT / "scripts" / "security" / "emit_security_event_allowlist.txt"

NEEDLE = "emit_security_event("
DEF_LINE = re.compile(r"^\s*def\s+emit_security_event\s*\(")


def _load_allowlist() -> set[str]:
    if not ALLOWLIST_FILE.is_file():
        print(f"ERROR: missing allowlist file: {ALLOWLIST_FILE}", file=sys.stderr)
        sys.exit(2)
    out: set[str] = set()
    for raw in ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.replace("\\", "/"))
    return out


def main() -> int:
    allow = _load_allowlist()
    violations: list[tuple[str, int, str]] = []
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR reading {rel}: {exc}", file=sys.stderr)
            return 2
        for lineno, line in enumerate(text.splitlines(), start=1):
            if NEEDLE not in line:
                continue
            if DEF_LINE.search(line):
                continue
            if rel in allow:
                continue
            violations.append((rel, lineno, line.strip()))

    if violations:
        print(
            "Raw emit_security_event( found outside allowlist.\n"
            "Use emit_security_event_v1 for new security events.\n"
            "See docs/security/security-events-governance.md\n",
            file=sys.stderr,
        )
        for rel, lineno, line in violations:
            print(f"  {rel}:{lineno}: {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
