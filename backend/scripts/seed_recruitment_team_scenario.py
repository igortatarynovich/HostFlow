#!/usr/bin/env python3
"""
CLI: seed dev/staging DB with Recruitment Team Flow scenario.

Usage (repository root = HostFlow, where `backend/` lives):

    PYTHONPATH=. python3 backend/scripts/seed_recruitment_team_scenario.py

Options:

    --reset-candidates   Delete only seed leads (`*@scenario-lead.local`) then re-create.
    --print-json         Print machine-readable summary (stderr still has hints).

Environment:

    RECRUIT_FLOW_SCENARIO_PASSWORD
    RECRUIT_FLOW_SCENARIO_TENANT_ID
    ASYNC_DATABASE_URL / DATABASE_URL (via backend settings)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env", override=False)
    load_dotenv(_REPO_ROOT / "backend" / ".env", override=False)
except ImportError:
    pass

# Compose hostname `db` often does not resolve on the host — mirror pytest conftest behaviour.
def _localize_db_host_env() -> None:
    import os
    import re
    import socket

    if (os.environ.get("HOSTFLOW_TEST_DB_HOST") or os.environ.get("PYTEST_DB_HOST") or "").strip():
        return
    try:
        socket.getaddrinfo("db", 5432, type=socket.SOCK_STREAM)
        return
    except OSError:
        pass
    for key in ("ASYNC_DATABASE_URL", "DATABASE_URL", "SYNC_DATABASE_URL"):
        val = os.environ.get(key)
        if val and "@db:" in val:
            os.environ[key] = re.sub(r"@db:", "@127.0.0.1:", val)


async def _run(*, reset_candidates: bool, tenant_id: str | None) -> dict:
    _localize_db_host_env()
    from backend.app.db.seeds.recruitment_team_flow_scenario import run_recruitment_team_flow_scenario
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        return await run_recruitment_team_flow_scenario(
            session,
            tenant_id=tenant_id,
            reset_candidates=reset_candidates,
        )


def main() -> None:
    p = argparse.ArgumentParser(description="Seed Recruitment Team Flow scenario (tenant, users, leads).")
    p.add_argument(
        "--reset-candidates",
        action="store_true",
        help="Remove seed candidates (*@scenario-lead.local) for this tenant, then recreate.",
    )
    p.add_argument("--tenant-id", type=str, default=None, help="Override tenant UUID (default: scenario id).")
    p.add_argument("--print-json", action="store_true", help="Print JSON summary to stdout.")
    args = p.parse_args()

    out = asyncio.run(_run(reset_candidates=args.reset_candidates, tenant_id=args.tenant_id))

    if args.print_json:
        print(json.dumps(out, indent=2))
    else:
        print("[recruit-flow-scenario] Seeded OK.")
        print(f"  tenant_id: {out['tenant_id']}")
        print(f"  password:  {out['password']}")
        print("  Logins:")
        for key in ("admin", "supervisor", "recruiter_a", "recruiter_b", "hr_officer"):
            u = out["users"][key]
            print(f"    - {u['email']}")
        print("  Unassigned queue URL:")
        print(f"    {out['ui']['candidates_unassigned_filter']}")


if __name__ == "__main__":
    main()
