#!/usr/bin/env python3
"""One-shot collapse of unread entity duplicates + retention purge."""
from __future__ import annotations

import asyncio
import json
import sys


async def main() -> int:
    from backend.app.core.settings import settings
    from backend.app.db.session import async_session_maker
    from backend.app.services.notification_retention import (
        collapse_entity_unread_duplicates,
        enforce_unread_caps_all_users,
        purge_expired_notifications,
        redis_lock,
    )

    settings.notifications_retention_batch_size = 10000
    settings.notifications_retention_max_batches_per_run = 2000

    async with redis_lock(ttl_sec=7200) as acquired:
        print(json.dumps({"lock_acquired": acquired}), flush=True)
        if not acquired:
            return 2
        async with async_session_maker() as db:
            collapsed = await collapse_entity_unread_duplicates(
                db, batch_size=10000, max_batches=2000
            )
            print(json.dumps({"collapsed": collapsed}), flush=True)
            purged = await purge_expired_notifications(db, max_batches=2000)
            print(json.dumps({"purged": purged}), flush=True)
            caps = await enforce_unread_caps_all_users(db)
            print(json.dumps({"caps": caps}), flush=True)
            await db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
