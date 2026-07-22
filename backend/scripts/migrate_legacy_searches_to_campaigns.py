#!/usr/bin/env python3
"""PR-A: dry-run / apply / rollback Legacy Search → Campaign + Flight.

Default mode is dry-run. Idempotency is stamp-only; rollback never deletes stamp.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.acquisition.legacy_search_migration import (  # noqa: E402
    SCRIPT_VERSION,
    migrate_all,
    rollback_all,
)
from backend.app.db.session import async_session_maker  # noqa: E402


async def _run(args: argparse.Namespace) -> int:
    dry_run = not args.apply
    async with async_session_maker() as db:
        if args.rollback:
            report = await rollback_all(
                db,
                tenant_id=args.tenant_id or None,
                vacancy_id=args.vacancy_id or None,
                dry_run=dry_run,
            )
        else:
            report = await migrate_all(
                db,
                tenant_id=args.tenant_id or None,
                vacancy_id=args.vacancy_id or None,
                dry_run=dry_run,
            )
        if args.apply:
            await db.commit()

    payload = report.to_dict()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"[{SCRIPT_VERSION}] json report: {out}")
    else:
        print(text)

    summary = payload["summary"]
    print(
        f"[{SCRIPT_VERSION}] mode={payload['mode']} "
        f"found={summary['found']} migrated={summary['migrated']} "
        f"already_existed={summary['already_existed']} "
        f"already_existed_rolled_back={summary['already_existed_rolled_back']} "
        f"needs_manual={summary['needs_manual']} "
        f"rolled_back={summary['rolled_back']} errors={summary['errors']}"
    )
    return 1 if summary["errors"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate eligible legacy Searches (Vacancy acquisition) to "
            "Campaign + Flight. Default: dry-run."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes (default is dry-run).",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help=(
            "Archive migration-owned Campaigns and stamp rolled_back_at "
            "(never delete stamp)."
        ),
    )
    parser.add_argument("--tenant-id", default="", help="Limit to one tenant.")
    parser.add_argument("--vacancy-id", default="", help="Limit to one vacancy.")
    parser.add_argument("--json", default="", help="Write full JSON report to path.")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
