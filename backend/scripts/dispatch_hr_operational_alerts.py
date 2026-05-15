#!/usr/bin/env python3
"""Worker CLI: dispatch HR operational alerts (v1).

Reads risk via ``hr_operational_risk``, emits throttled in-app notifications + audit.
No HTTP. Intended for cron/systemd/K8s CronJob.

Default without ``--apply`` is **dry-run** (audit-only summary per tenant, no bell spam).

Examples::

    python3 backend/scripts/dispatch_hr_operational_alerts.py
    python3 backend/scripts/dispatch_hr_operational_alerts.py --tenant <uuid> --apply
    HR_OPERATIONAL_ALERTS_ACTOR_ID=system:my_scheduler python3 backend/scripts/dispatch_hr_operational_alerts.py --apply
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

from backend.app.jobs.hr_operational_alerts_dispatch import (
    dispatch_hr_operational_alerts_all_tenants,
)


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def _run(args: argparse.Namespace) -> int:
    dry_run = not bool(args.apply)
    summary = await dispatch_hr_operational_alerts_all_tenants(
        tenant_id=args.tenant,
        dry_run=dry_run,
        horizon_days=int(args.horizon_days),
        assignee_scope=str(args.assignee_scope),
        actor_id=args.actor_id,
        viewer_id=args.viewer_id,
        viewer_role=args.viewer_role,
    )
    if args.json:
        print(json.dumps(summary, default=str, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tenant",
        metavar="UUID",
        help="Single tenant id. If omitted, all tenants are processed sequentially.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create notifications + dispatch audit. Without this flag, dry-run only.",
    )
    parser.add_argument("--horizon-days", type=int, default=90, help="Risk horizon (default 90).")
    parser.add_argument(
        "--assignee-scope",
        default="team",
        help="Dashboard-style assignee scope (default team).",
    )
    parser.add_argument(
        "--actor-id",
        default=None,
        help=(
            "Audit/security actor id (default: env HR_OPERATIONAL_ALERTS_ACTOR_ID "
            "or system:hr_operational_alerts_dispatch)."
        ),
    )
    parser.add_argument(
        "--viewer-id",
        default=None,
        help="Optional: override synthetic risk viewer user id (must pair with --viewer-role).",
    )
    parser.add_argument(
        "--viewer-role",
        default=None,
        help="Optional: override synthetic risk viewer role (e.g. hr_officer).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable summary JSON to stdout.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args()
    if (args.viewer_id or args.viewer_role) and not (args.viewer_id and args.viewer_role):
        parser.error("--viewer-id and --viewer-role must be passed together")
    _configure_logging(bool(args.verbose))
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
