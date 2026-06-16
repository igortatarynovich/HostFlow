#!/usr/bin/env python3
"""Report deprecated foundation token backlog in src/ (non-blocking, exit 0 always)."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from foundation_tokens_lib import SRC_SUFFIXES, find_in_text, scrub_suppressed_lines

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def main() -> int:
    by_category: Counter[str] = Counter()
    total = 0

    for path in sorted(SRC.rglob("*")):
        if path.suffix not in SRC_SUFFIXES or not path.is_file():
            continue
        text = scrub_suppressed_lines(path.read_text(encoding="utf-8", errors="ignore"))
        for item in find_in_text(text, file=str(path.relative_to(ROOT))):
            by_category[item.category] += 1
            total += 1

    print("=== FOUNDATION DEPRECATED SCAN (non-blocking) ===")
    for category in ("spacing", "typography", "colors", "radius", "shadow", "breakpoints"):
        print(f"  {category}: {by_category[category]}")
    print(f"  TOTAL: {total}")
    print("Target: 0 (see docs/specs/frontend/FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
