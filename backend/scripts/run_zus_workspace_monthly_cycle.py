#!/usr/bin/env python3
"""Worker CLI: create idempotent ZUS workspace monthly settlement tasks per employee.

No HTTP, no ZUS API. Intended for cron/systemd/K8s CronJob (e.g. first business day of month).

Examples::

    python3 backend/scripts/run_zus_workspace_monthly_cycle.py --period 2026-05 --dry-run
    python3 backend/scripts/run_zus_workspace_monthly_cycle.py --period 2026-05 --apply
    python3 backend/scripts/run_zus_workspace_monthly_cycle.py --tenant <uuid> --period 202605 --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
if THIS.parent.name == "scripts" and THIS.parent.parent.name == "backend":
    BACKEND_DIR = THIS.parent.parent
    PROJECT_ROOT = BACKEND_DIR.parent
else:
    PROJECT_ROOT = THIS.parent.parent
    BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.jobs.zus_workspace_monthly_cycle import run_monthly_zus_workspace_all_tenants


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def _run(args: argparse.Namespace) -> int:
    dry_run = not bool(args.apply)
    summary = await run_monthly_zus_workspace_all_tenants(
        period_yyyy_mm=str(args.period).strip(),
        tenant_id=(str(args.tenant).strip() if args.tenant else None),
        dry_run=dry_run,
        actor_id=(str(args.actor_id).strip() if args.actor_id else None),
    )
    if args.json:
        print(json.dumps(summary, default=str, indent=2))
    else:
        logging.getLogger(__name__).info(
            "zus_workspace_monthly_cycle done tenants=%s dry_run=%s total_created=%s total_would=%s",
            summary.get("tenants"),
            summary.get("dry_run"),
            summary.get("total_tasks_created"),
            summary.get("total_would_create"),
        )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--period",
        required=True,
        metavar="YYYY-MM|YYYYMM",
        help="Billing / settlement month label (stored on task checklist_json.period).",
    )
    parser.add_argument("--tenant", metavar="UUID", help="Limit to one tenant.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist tasks + audit. Without this flag, dry-run only (counts would_create).",
    )
    parser.add_argument(
        "--actor-id",
        dest="actor_id",
        metavar="STRING",
        help="Security job context actor (RLS session). ActivityLog uses null actor for auto rows.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    _configure_logging(bool(args.verbose))
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
