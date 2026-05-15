#!/usr/bin/env python3
"""
Merge gate: discourage logging obvious secret/surface strings next to logger calls.

Same-line heuristic (intentionally narrow): ``logger.<level>(`` on a line that also
mentions one of the forbidden substrings (case-insensitive). Catches ad-hoc
``logger.info("url=%s", signed_url)`` style bypasses of canonical security events.

Does not parse multi-line calls; prefer structured security_event logging instead.

Run from repo root::

    python3 scripts/security/check_no_sensitive_logger_bypass.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = REPO_ROOT / "backend" / "app"

LOGGER_CALL = re.compile(r"\blogger\.(trace|debug|info|warning|error|critical|exception)\s*\(", re.IGNORECASE)
FORBIDDEN_SUBSTRINGS = ("signed_url", "download_url", "export_path", "archive_path")


def main() -> int:
    violations: list[tuple[str, int, str]] = []
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR reading {rel}: {exc}", file=sys.stderr)
            return 2
        lower = text.lower()
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not LOGGER_CALL.search(line):
                continue
            low_line = line.lower()
            hit = next((s for s in FORBIDDEN_SUBSTRINGS if s in low_line), None)
            if not hit:
                continue
            # Allow mentioning the substring only inside a quoted log tag, e.g.
            # logger.info("[uploads] presign failed ...") — still avoid if variable name present
            violations.append((rel, lineno, line.strip()))
    if violations:
        print(
            "Logger call on same line as sensitive substring "
            f"{FORBIDDEN_SUBSTRINGS}.\n"
            "Use emit_security_event_v1 / document_events / export_events instead of raw logs.\n"
            "See docs/security/telemetry-phase3-4-mandatory-events.md\n",
            file=sys.stderr,
        )
        for rel, lineno, line in violations:
            print(f"  {rel}:{lineno}: {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
