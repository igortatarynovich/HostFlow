#!/usr/bin/env python3
"""Repair Questionnaire SSOT for targeted-advertising forms on a tenant."""

from __future__ import annotations

import asyncio
import json
import sys

from backend.app.db.session import async_session_maker
from backend.app.services.questionnaire_ssot_repair import repair_targeted_advertising_questionnaires


async def main() -> None:
    if len(sys.argv) != 2:
        print("usage: repair_targeted_advertising_capability.py <tenant_id>", file=sys.stderr)
        raise SystemExit(2)
    tenant_id = sys.argv[1].strip()
    async with async_session_maker() as db:
        result = await repair_targeted_advertising_questionnaires(db, tenant_id=tenant_id)
        if result.status == "failed":
            await db.rollback()
            print(json.dumps(result.__dict__, ensure_ascii=False))
            raise SystemExit(1)
        await db.commit()
        print(json.dumps(result.__dict__, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
