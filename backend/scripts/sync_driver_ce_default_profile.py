#!/usr/bin/env python3
"""Force-sync driver_ce_default stage pipeline for all active tenants."""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant
from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile


async def main() -> None:
    async with async_session_maker() as db:
        tenants = (
            await db.execute(
                select(Tenant.id).where(Tenant.is_active == True)  # noqa: E712
            )
        ).scalars().all()
        if not tenants:
            print("No active tenants found.")
            return

        for tenant_id in tenants:
            tid = str(tenant_id)
            print(f"Syncing tenant {tid}...")
            await ensure_driver_ce_default_profile(db, tid)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
