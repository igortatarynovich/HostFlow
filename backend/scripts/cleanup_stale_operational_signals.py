#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import or_, select

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

from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES
from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.tenant import Tenant
from backend.app.services.candidate_lifecycle import apply_candidate_terminal_cleanup
from backend.app.services.lead_lifecycle import (
    LEAD_TERMINAL_STAGE_CODES,
    LEAD_TERMINAL_STATUS_CODES,
    apply_lead_terminal_cleanup,
)


async def _tenant_ids(target_tenant: str | None) -> list[str]:
    tid = (target_tenant or "").strip()
    if tid:
        return [tid]
    async with async_session_maker() as db:
        rows = await db.execute(select(Tenant.id))
        return [str(row[0]) for row in rows.all() if row and row[0]]


async def _cleanup_for_tenant(tenant_id: str, *, apply: bool) -> dict[str, int]:
    stats = {
        "candidate_rows": 0,
        "lead_rows": 0,
        "reminders_cancelled": 0,
        "notifications_marked_read": 0,
        "planner_events_cancelled": 0,
    }
    async with async_session_maker() as db:
        cand_rows = await db.execute(
            select(Candidate.id).where(
                Candidate.tenant_id == tenant_id,
                or_(
                    Candidate.stage.in_(tuple(PIPELINE_COMPLETED_STAGE_CODES)),
                    Candidate.deleted_at.is_not(None),
                ),
            )
        )
        candidate_ids = [str(row[0]) for row in cand_rows.all() if row and row[0]]
        stats["candidate_rows"] = len(candidate_ids)

        lead_rows = await db.execute(
            select(Lead.id).where(
                Lead.tenant_id == tenant_id,
                or_(
                    Lead.candidate_id.is_not(None),
                    Lead.stage.in_(tuple(LEAD_TERMINAL_STAGE_CODES)),
                    Lead.status.in_(tuple(LEAD_TERMINAL_STATUS_CODES)),
                ),
            )
        )
        lead_ids = [str(row[0]) for row in lead_rows.all() if row and row[0]]
        stats["lead_rows"] = len(lead_ids)

        if not apply:
            return stats

        for candidate_id in candidate_ids:
            res = await apply_candidate_terminal_cleanup(
                db,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                new_stage=None,
                actor_id="system-backfill",
                reason="backfill_stale_signals",
            )
            stats["reminders_cancelled"] += int(res.reminders_cancelled or 0)
            stats["notifications_marked_read"] += int(res.notifications_marked_read or 0)
            stats["planner_events_cancelled"] += int(res.planner_events_cancelled or 0)

        for lead_id in lead_ids:
            res = await apply_lead_terminal_cleanup(
                db,
                tenant_id=tenant_id,
                lead_id=lead_id,
                new_stage=None,
                new_status=None,
                actor_id="system-backfill",
                reason="backfill_stale_signals",
            )
            stats["reminders_cancelled"] += int(res.reminders_cancelled or 0)
            stats["notifications_marked_read"] += int(res.notifications_marked_read or 0)
            stats["planner_events_cancelled"] += int(res.planner_events_cancelled or 0)

        await db.commit()
    return stats


async def main_async(tenant: str | None, *, apply: bool) -> int:
    tenant_ids = await _tenant_ids(tenant)
    if not tenant_ids:
        print("No tenants found.")
        return 0

    grand = {
        "candidate_rows": 0,
        "lead_rows": 0,
        "reminders_cancelled": 0,
        "notifications_marked_read": 0,
        "planner_events_cancelled": 0,
    }

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[cleanup_stale_operational_signals] mode={mode} tenants={len(tenant_ids)}")
    for tenant_id in tenant_ids:
        stats = await _cleanup_for_tenant(tenant_id, apply=apply)
        for k in grand:
            grand[k] += int(stats[k] or 0)
        print(
            f"tenant={tenant_id} candidate_rows={stats['candidate_rows']} lead_rows={stats['lead_rows']} "
            f"reminders_cancelled={stats['reminders_cancelled']} "
            f"notifications_marked_read={stats['notifications_marked_read']} "
            f"planner_events_cancelled={stats['planner_events_cancelled']}"
        )

    print(
        "TOTAL "
        f"candidate_rows={grand['candidate_rows']} lead_rows={grand['lead_rows']} "
        f"reminders_cancelled={grand['reminders_cancelled']} "
        f"notifications_marked_read={grand['notifications_marked_read']} "
        f"planner_events_cancelled={grand['planner_events_cancelled']}"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup stale operational signals for terminal candidates/leads.")
    parser.add_argument("--tenant", help="Tenant UUID (optional). If omitted, process all tenants.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply cleanup changes. Without this flag, script runs as dry-run.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args.tenant, apply=args.apply)))


if __name__ == "__main__":
    main()
