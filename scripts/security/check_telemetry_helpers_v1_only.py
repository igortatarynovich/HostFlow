#!/usr/bin/env python3
"""
Merge gate: document / export / retrieval telemetry modules must only call canonical v1.

- Must import ``emit_security_event_v1`` from ``backend.app.security.canonical_emit``.
- Must not call legacy ``emit_security_event(`` or import it from ``security.events``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FILES = [
    REPO_ROOT / "backend" / "app" / "security" / "document_events.py",
    REPO_ROOT / "backend" / "app" / "security" / "export_events.py",
    REPO_ROOT / "backend" / "app" / "security" / "retrieval_events.py",
]

IMPORT_V1 = re.compile(
    r"from\s+backend\.app\.security\.canonical_emit\s+import\s+[^\n]*\bemit_security_event_v1\b",
)
FROM_EVENTS = re.compile(
    r"^\s*from\s+backend\.app\.security\.events\s+import\b",
    re.MULTILINE,
)
RAW_CALL = re.compile(r"\bemit_security_event\s*\(\s*")


def main() -> int:
    errors: list[str] = []
    for path in FILES:
        rel = path.relative_to(REPO_ROOT).as_posix()
        if not path.is_file():
            errors.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if not IMPORT_V1.search(text):
            errors.append(f"{rel}: must import emit_security_event_v1 from backend.app.security.canonical_emit")
        if FROM_EVENTS.search(text):
            errors.append(f"{rel}: must not import from backend.app.security.events (legacy shim)")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if RAW_CALL.search(line) and "emit_security_event_v1" not in line:
                if re.match(r"^\s*def\s+emit_security_event\s*\(", line):
                    continue
                errors.append(f"{rel}:{lineno}: raw emit_security_event( call is forbidden: {line.strip()}")
    if errors:
        print("Telemetry helper gate failed:\n", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
