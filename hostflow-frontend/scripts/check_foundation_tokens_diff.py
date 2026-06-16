#!/usr/bin/env python3
"""Block deprecated foundation tokens in git diff added lines (CI)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from foundation_tokens_lib import SRC_SUFFIXES, find_in_text, invalid_allow_lines, line_suppressed

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def resolve_base() -> str:
    base = os.environ.get("FOUNDATION_DIFF_BASE", "origin/main")
    for candidate in (base, "origin/main", "main", "HEAD~1"):
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            return candidate
        except subprocess.CalledProcessError:
            continue
    print("check-foundation-tokens: no git diff base found; skipping.", file=sys.stderr)
    sys.exit(0)


def list_src_files() -> list[str]:
    paths: list[str] = []
    for path in SRC.rglob("*"):
        if path.suffix in SRC_SUFFIXES and path.is_file():
            paths.append(str(path.relative_to(ROOT)))
    return paths


def parse_diff(base: str) -> list[tuple[str, int, str, str]]:
    """Return (file, line, added_line, previous_line) tuples from unified diff."""
    cmd = ["git", "diff", "--unified=0", f"{base}...HEAD", "--", *list_src_files()]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode > 1:
        cmd = ["git", "diff", "--unified=0", f"{base}...HEAD", "--", "src"]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)

    entries: list[tuple[str, int, str, str]] = []
    current_file = ""
    line_no = 0
    previous = ""

    for raw in result.stdout.splitlines():
        if raw.startswith("diff --git "):
            m = re.search(r" b/(.*)$", raw)
            current_file = m.group(1) if m else ""
            previous = ""
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) if m else 0
            previous = ""
            continue
        if not raw.startswith("+"):
            continue

        added = raw[1:]
        entries.append((current_file, line_no, added, previous))
        previous = added
        line_no += 1

    return entries


def main() -> int:
    base = resolve_base()
    findings = []

    for file, line_no, added, previous in parse_diff(base):
        if not file or not any(file.endswith(s) for s in SRC_SUFFIXES):
            continue

        for item in invalid_allow_lines(added, file=file):
            findings.append((file, line_no, item.category, item.token, item.snippet))

        if line_suppressed(added, previous):
            continue
        for item in find_in_text(added, file=file):
            findings.append((file, line_no, item.category, item.token, item.snippet))

    if not findings:
        print(f"check-foundation-tokens: diff clean (base: {base}).")
        return 0

    print(f"check-foundation-tokens: {len(findings)} deprecated foundation token(s) in diff (base: {base}).\n")
    for file, line_no, category, token, snippet in findings:
        print(f"  {file}:{line_no} [{category}] {token}")
        print(f"    {snippet}")

    print(
        "\nNew deprecated foundation tokens are forbidden."
        "\nSuppress only with: foundation-allow: <reason, min 8 chars>"
        "\nSee docs/specs/frontend/FOUNDATION_V1.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
