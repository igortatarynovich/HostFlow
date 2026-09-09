#!/usr/bin/env python3
"""Backfill Meta leads → Acquisition activity + result attribution.

Heals Marketing Sources last_lead and portfolio lead KPIs for tenants whose Meta
ingest predated ``project_meta_lead_into_acquisition``.

Usage (repo root, with DATABASE_URL / ASYNC_DATABASE_URL set):

  .venv312/bin/python scripts/backfill_meta_lead_acquisition_projections.py \\
      --tenant-id 11111111-1111-1111-1111-111111111111

  .venv312/bin/python scripts/backfill_meta_lead_acquisition_projections.py --all-tenants
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))


async def _run(*, tenant_ids: list[str] | None, limit: int, commit: bool) -> int:
    from sqlalchemy import select, text

    from backend.app.acquisition.meta_lead_projections import backfill_meta_lead_projections
    from backend.app.db.session import async_session_maker
    from backend.app.models.tenant import Tenant

    async with async_session_maker() as db:
        if tenant_ids is None:
            rows = (await db.execute(select(Tenant.id).where(Tenant.is_active.is_(True)))).scalars().all()
            tenant_ids = [str(r) for r in rows]

        grand = {"tenants": 0, "scanned": 0, "projected": 0, "skipped_no_campaign": 0}
        for tid in tenant_ids:
            await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tid})
            stats = await backfill_meta_lead_projections(db, tenant_id=tid, limit=limit)
            print(f"tenant={tid} {stats}")
            grand["tenants"] += 1
            for k in ("scanned", "projected", "skipped_no_campaign"):
                grand[k] += int(stats.get(k, 0))
        if commit:
            await db.commit()
            print(f"COMMITTED {grand}")
        else:
            await db.rollback()
            print(f"DRY-RUN (rolled back) {grand}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--tenant-id", action="append", dest="tenant_ids")
    g.add_argument("--all-tenants", action="store_true")
    p.add_argument("--limit", type=int, default=5000)
    p.add_argument(
        "--commit",
        action="store_true",
        help="Persist changes (default is dry-run / rollback).",
    )
    args = p.parse_args()
    if not (os.getenv("ASYNC_DATABASE_URL") or os.getenv("DATABASE_URL")):
        print("ERROR: set ASYNC_DATABASE_URL or DATABASE_URL", file=sys.stderr)
        return 2
    return asyncio.run(
        _run(
            tenant_ids=None if args.all_tenants else list(args.tenant_ids or []),
            limit=args.limit,
            commit=bool(args.commit),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
