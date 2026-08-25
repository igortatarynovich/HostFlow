#!/usr/bin/env python3
"""
Merge gate: Phase 6 retrieval call sites must use emit_retrieval_security_event_v1.

Required producers (must contain the helper call):
  - backend/app/api/v1/global_search.py
  - backend/app/api/v1/tenants/router.py (links/search-companies)

Run from repo root::

    python3 scripts/security/check_retrieval_call_sites.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    REPO_ROOT / "backend" / "app" / "api" / "v1" / "global_search.py",
    REPO_ROOT / "backend" / "app" / "api" / "v1" / "tenants" / "router.py",
]
NEEDLE = "emit_retrieval_security_event_v1"


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED:
        rel = path.relative_to(REPO_ROOT).as_posix()
        if not path.is_file():
            errors.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if NEEDLE not in text:
            errors.append(f"{rel}: must call {NEEDLE}")
        if "search.retrieval" not in text and "EVENT_SEARCH_RETRIEVAL" not in text:
            errors.append(f"{rel}: must reference search.retrieval event types")
    if errors:
        print(
            "Retrieval call-site gate failed (Phase 6).\n"
            "See docs/security/retrieval-audit-governance.md\n",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
