#!/usr/bin/env python3
"""Bulk retry Lead-stage art.14 RODO via Communication Pipeline (ADR-031).

Example (dry-run):
  PYTHONPATH=. python backend/scripts/retry_lead_rodo.py \\
    --tenant 9497fc29-6051-424d-9344-abb4aed9b110 --dry-run --limit 50

Live send (failed only, default):
  PYTHONPATH=. python backend/scripts/retry_lead_rodo.py \\
    --tenant 9497fc29-6051-424d-9344-abb4aed9b110 --limit 50
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

THIS = Path(__file__).resolve()
# Local: <repo>/backend/scripts/foo.py → repo root.
# Docker: /app/backend → /app symlink, so scripts resolve under /app/scripts.
_parent = THIS.parent.parent
if (_parent / "app" / "__init__.py").is_file() or (_parent / "app" / "main.py").is_file():
    PROJECT_ROOT = _parent
elif (_parent.parent / "backend" / "app").is_dir():
    PROJECT_ROOT = _parent.parent
else:
    PROJECT_ROOT = _parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text  # noqa: E402

from backend.app.core.settings import settings  # noqa: F401,E402
import backend.app.models  # noqa: F401,E402 — configure ORM relationship targets
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.services.lead_rodo_bulk_retry import (  # noqa: E402
    bulk_retry_lead_rodo,
    summarize_bulk_retry,
)


def _parse_list(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    out = [str(v).strip() for v in values if str(v).strip()]
    return out or None


async def _run(
    *,
    tenant_id: str,
    lead_ids: Optional[List[str]],
    statuses: Optional[List[str]],
    limit: int,
    include_terminal: bool,
    dry_run: bool,
) -> None:
    async with async_session_maker() as session:
        await session.execute(text("SELECT set_config('app.bypass_rls', 'true', true)"))
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": tenant_id},
        )
        result = await bulk_retry_lead_rodo(
            session,
            tenant_id=tenant_id,
            actor_id=None,
            lead_ids=lead_ids,
            statuses=statuses,
            max_items=limit,
            include_terminal=include_terminal,
            dry_run=dry_run,
        )
        if not dry_run:
            await session.commit()
        print(json.dumps(summarize_bulk_retry(result), indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk retry Lead RODO (art.14) via Pipeline.")
    parser.add_argument("--tenant", required=True, help="Tenant UUID")
    parser.add_argument("--lead", action="append", dest="leads", help="Specific lead ID (repeatable)")
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="delivery_failed | delivery_required (legacy failed | pending_channel map to delivery_failed). Default: delivery_failed. review_required is rejected.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Max leads (1..200)")
    parser.add_argument("--include-terminal", action="store_true", help="Include processed/rejected/…")
    parser.add_argument("--dry-run", action="store_true", help="List only, do not send")
    args = parser.parse_args()

    asyncio.run(
        _run(
            tenant_id=str(args.tenant).strip(),
            lead_ids=_parse_list(args.leads),
            statuses=_parse_list(args.statuses),
            limit=int(args.limit),
            include_terminal=bool(args.include_terminal),
            dry_run=bool(args.dry_run),
        )
    )


if __name__ == "__main__":
    main()
