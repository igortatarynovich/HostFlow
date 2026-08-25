#!/usr/bin/env python3
"""
Merge gate: ARQ tenant-scoped jobs must use tenant_enforced_session / job tenant parse.

Checks ``backend/app/core/arq_worker.py``:
1. ``job_calendar_sync_ingest`` and ``job_automation_evaluate_trigger`` reference
   ``tenant_enforced_session`` and ``parse_required_job_tenant_id``.
2. ``job_stripe_webhook_process`` / ``job_communications_dispatch_once`` reference
   ``security_job_context`` (platform or multi-tenant tick).

Run from repo root::

    python3 scripts/security/check_arq_worker_tenant.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKER = REPO_ROOT / "backend" / "app" / "core" / "arq_worker.py"


def main() -> int:
    if not WORKER.is_file():
        print(f"ERROR: missing {WORKER}", file=sys.stderr)
        return 2
    text = WORKER.read_text(encoding="utf-8")
    errors: list[str] = []

    for fn, needles in (
        (
            "job_calendar_sync_ingest",
            ("tenant_enforced_session", "parse_required_job_tenant_id"),
        ),
        (
            "job_automation_evaluate_trigger",
            ("tenant_enforced_session", "parse_required_job_tenant_id"),
        ),
        ("job_stripe_webhook_process", ("security_job_context",)),
        ("job_communications_dispatch_once", ("security_job_context",)),
    ):
        if f"async def {fn}" not in text:
            errors.append(f"missing function {fn}")
            continue
        # Rough function body slice until next async def job_ or end.
        start = text.index(f"async def {fn}")
        rest = text[start + 1 :]
        nxt = rest.find("\nasync def job_")
        body = rest if nxt < 0 else rest[:nxt]
        for needle in needles:
            if needle not in body:
                errors.append(f"{fn}: must reference {needle}")

    if errors:
        print(
            "ARQ worker tenant context gate failed (SSOT §0b).\n"
            "Tenant-scoped jobs need tenant_enforced_session + parse_required_job_tenant_id.\n"
            "Platform jobs need security_job_context.\n",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
