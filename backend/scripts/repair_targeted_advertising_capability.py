#!/usr/bin/env python3
"""Repair / lazy-ensure targeted-advertising capability for a services tenant."""

from __future__ import annotations

import asyncio
import json
import sys

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.provision_targeted_advertising import recover_targeted_advertising_capability


async def main() -> None:
    if len(sys.argv) != 2:
        print("usage: repair_targeted_advertising_capability.py <tenant_id>", file=sys.stderr)
        raise SystemExit(2)
    tenant_id = sys.argv[1].strip()
    async with async_session_maker() as db:
        result = await recover_targeted_advertising_capability(db, tenant_id)
        if result.status == "failed":
            await db.rollback()
            print(json.dumps({"status": result.status, "error": result.error}, ensure_ascii=False))
            raise SystemExit(1)
        await db.commit()
        print(
            json.dumps(
                {
                    "status": result.status,
                    "tenant_id": result.tenant_id,
                    "lead_form_id": result.lead_form_id,
                    "created": result.created,
                    "repaired": result.repaired,
                    "skipped": result.skipped,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
