#!/usr/bin/env python3
"""Register missing Entity Profile manifests for active tenants."""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Preload the FastAPI app so entity_profile package imports resolve (avoids circular import).
import backend.app.main  # noqa: F401

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.tenant import Tenant
from backend.app.services.launch_search_role_defaults import ensure_launch_search_role_defaults


async def main() -> None:
    async with async_session_maker() as db:
        tenant_ids = (
            await db.execute(select(Tenant.id).where(Tenant.is_active == True))  # noqa: E712
        ).scalars().all()
        for tenant_id in tenant_ids:
            tid = str(tenant_id)
            print(f"Seeding entity profiles for tenant {tid}...")
            await ensure_tenant_entity_profile_defaults(db, tid)
            await db.commit()
            try:
                await ensure_launch_search_role_defaults(db, tid)
            except Exception as exc:
                print(f"  launch_search_role_defaults skipped: {exc}")
                await db.rollback()
            else:
                print(f"  launch_search_role_defaults ok")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
