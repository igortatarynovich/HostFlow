#!/usr/bin/env python3
"""One-shot / cron entry for in-app notification retention purge.

Examples:
  python -m backend.scripts.purge_notifications_retention
  docker exec hostflow-backend-1 python -m backend.scripts.purge_notifications_retention
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


async def _main(tenant_id: str | None, max_batches: int | None) -> int:
    from backend.app.services.notification_retention import run_notifications_retention_once

    stats = await run_notifications_retention_once(
        tenant_id=tenant_id,
        max_batches=max_batches,
    )
    print(json.dumps(stats, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purge expired in-app notifications")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Override notifications_retention_max_batches_per_run for this run",
    )
    args = parser.parse_args(argv)
    return asyncio.run(_main(args.tenant_id, args.max_batches))


if __name__ == "__main__":
    sys.exit(main())
