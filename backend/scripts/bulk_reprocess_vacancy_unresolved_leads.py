#!/usr/bin/env python3
"""
CLI: mass-reprocess Meta/csv_import leads via the same pipeline as POST /leads/bulk/auto-process-queue.

Default mode: error=VACANCY_NOT_RESOLVED, only rows without candidate_id (legacy helper name).

Full «Требует маршрутизации» backlog (all needs_routing, any error text):
  python3 backend/scripts/bulk_reprocess_vacancy_unresolved_leads.py \\
    --tenant-id <uuid> --no-error-filter --status needs_routing --loop --prefer-oldest

Dry-run:
  python3 backend/scripts/bulk_reprocess_vacancy_unresolved_leads.py --tenant-id <uuid> --dry-run

Database URL: run on a host that can resolve the DB hostname. If you see ``gaierror`` / ``Temporary failure in name resolution``
for host ``db``, you are outside Docker — set e.g.
``export ASYNC_DATABASE_URL=postgresql+asyncpg://USER:PASS@127.0.0.1:5432/DBNAME`` (and matching ``DATABASE_URL``).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

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

from backend.app.core.settings import settings  # noqa: F401
from backend.app.db.session import async_session_maker
from backend.app.modules.leads import service


def _parse_statuses(values: Optional[Sequence[str]]) -> Tuple[str, ...]:
    if not values:
        return ("needs_routing", "failed")
    out: List[str] = []
    for v in values:
        s = (v or "").strip().lower()
        if s:
            out.append(s)
    return tuple(out) if out else ("needs_routing", "failed")


async def _run(
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    max_per_round: int,
    statuses: Tuple[str, ...],
    error_equals: Optional[str],
    only_without_candidate: bool,
    loop_batches: bool,
    dry_run: bool,
    prefer_oldest_first: bool,
    concurrency: int,
    force_candidate_conversion: bool,
) -> None:
    # One short-lived session per count / per batch round — do NOT hold a connection across the whole
    # loop while workers open more sessions (pool starvation / long idle transactions).
    if dry_run:
        async with async_session_maker() as session:
            n = await service.count_bulk_auto_process_meta_lead_queue(
                session,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                statuses=statuses,
                only_without_candidate=only_without_candidate,
                error_equals=error_equals,
            )
        print(
            json.dumps(
                {
                    "matching_leads": n,
                    "statuses": list(statuses),
                    "error_equals": error_equals,
                    "only_without_candidate": only_without_candidate,
                },
                indent=2,
            ),
            flush=True,
        )
        return

    round_idx = 0
    grand: dict = {"attempted": 0, "succeeded": 0, "failed": 0, "rounds": []}
    while True:
        round_idx += 1
        async with async_session_maker() as session:
            remaining_before = await service.count_bulk_auto_process_meta_lead_queue(
                session,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                statuses=statuses,
                only_without_candidate=only_without_candidate,
                error_equals=error_equals,
            )
        if remaining_before == 0:
            print(json.dumps({"done": True, "reason": "queue_empty", "round": round_idx}, indent=2), flush=True)
            break

        async with async_session_maker() as session:
            raw = await service.bulk_auto_process_meta_lead_queue(
                session,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                max_items=max_per_round,
                statuses=statuses,
                prefer_oldest_first=prefer_oldest_first,
                only_without_candidate=only_without_candidate,
                error_equals=error_equals,
                concurrency=concurrency,
                force_candidate_conversion=force_candidate_conversion,
            )
        async with async_session_maker() as session:
            remaining_after = await service.count_bulk_auto_process_meta_lead_queue(
                session,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                statuses=statuses,
                only_without_candidate=only_without_candidate,
                error_equals=error_equals,
            )

        grand["attempted"] += int(raw["attempted"])
        grand["succeeded"] += int(raw["succeeded"])
        grand["failed"] += int(raw["failed"])
        row = {
            "round": round_idx,
            "remaining_before": remaining_before,
            "remaining_after": remaining_after,
            "attempted": raw["attempted"],
            "succeeded": raw["succeeded"],
            "failed": raw["failed"],
        }
        grand["rounds"].append(row)
        print(json.dumps({"progress": row, "totals": {k: grand[k] for k in ("attempted", "succeeded", "failed")}}), flush=True)

        if raw["attempted"] == 0:
            break
        # Pipeline can "succeed" but leave status needs_routing (fit / routing). Without this, --loop repeats the same IDs forever.
        if loop_batches and remaining_after >= remaining_before and raw["attempted"] > 0:
            print(
                json.dumps(
                    {
                        "stuck": True,
                        "message": "Queue size did not shrink after processing; leads likely still need manual routing or settings (fit/vacancy). Stopping --loop.",
                        "remaining_before": remaining_before,
                        "remaining_after": remaining_after,
                    },
                    indent=2,
                ),
                flush=True,
            )
            break
        if not loop_batches:
            break

    print(json.dumps(grand, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-reprocess Meta/csv_import leads (routing queue or VACANCY_NOT_RESOLVED subset)."
    )
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--own-company-id", default=None, help="Restrict to active own company (optional)")
    parser.add_argument("--max-per-round", type=int, default=50, help="Per call (1–50, same as API cap)")
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Lead status filter (repeatable). Default: needs_routing and failed",
    )
    parser.add_argument(
        "--no-error-filter",
        action="store_true",
        help="Do not filter by Lead.error (use for full «Требует маршрутизации» backlog).",
    )
    parser.add_argument(
        "--error",
        default="VACANCY_NOT_RESOLVED",
        help="Exact Lead.error when not using --no-error-filter (default: VACANCY_NOT_RESOLVED)",
    )
    parser.add_argument(
        "--include-with-candidate",
        action="store_true",
        help="Also process rows that already have candidate_id (default: only candidate_id IS NULL)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        dest="loop_batches",
        help="Repeat 50-at-a-time until no matching rows remain",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only count matching rows, do not process")
    parser.add_argument(
        "--prefer-oldest",
        action="store_true",
        dest="prefer_oldest_first",
        help="Order by created_at ascending (FIFO backlog)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=12,
        help="Parallel workers per batch (1=sequential; default 12, max 32). Lower if DB pool is small.",
    )
    parser.add_argument(
        "--force-convert",
        action="store_true",
        help="Create candidates even in assisted mode / when fit would block (needs resolvable vacancy + contacts).",
    )
    args = parser.parse_args()
    statuses = _parse_statuses(args.statuses)
    if args.no_error_filter:
        err: Optional[str] = None
    else:
        err = str(args.error or "").strip() or "VACANCY_NOT_RESOLVED"
    conc = max(1, min(int(args.concurrency or 12), 32))
    asyncio.run(
        _run(
            tenant_id=str(args.tenant_id).strip(),
            own_company_id=(str(args.own_company_id).strip() if args.own_company_id else None) or None,
            max_per_round=max(1, min(int(args.max_per_round or 50), 50)),
            statuses=statuses,
            error_equals=err,
            only_without_candidate=not bool(args.include_with_candidate),
            loop_batches=bool(args.loop_batches),
            dry_run=bool(args.dry_run),
            prefer_oldest_first=bool(args.prefer_oldest_first),
            concurrency=conc,
            force_candidate_conversion=bool(args.force_convert),
        )
    )


if __name__ == "__main__":
    main()
