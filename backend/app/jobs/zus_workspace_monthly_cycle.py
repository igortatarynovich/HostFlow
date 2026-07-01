"""Monthly ZUS workspace task generation (cron/worker; no payroll math)."""

from __future__ import annotations

import logging
import os
from uuid import UUID

from sqlalchemy import select

from backend.app.db.deps import tenant_enforced_session
from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services.workforce_zus_task_autocreate import ensure_zus_monthly_settlement_task

logger = logging.getLogger(__name__)

_DEFAULT_ACTOR = "system:zus_workspace_monthly"

_MONTHLY_EMPLOYEE_STATUSES = frozenset(
    {
        "onboarding",
        "active",
        "on_sick_leave",
        "on_vacation",
        "on_leave",
        "contract_ending",
    }
)


def default_monthly_actor_id() -> str:
    return (os.environ.get("ZUS_WORKSPACE_MONTHLY_ACTOR_ID") or _DEFAULT_ACTOR).strip()


async def list_tenant_ids_for_monthly(*, tenant_id: str | None) -> list[str]:
    one = (tenant_id or "").strip()
    if one:
        return [one]
    async with async_session_maker() as db:
        rows = await db.execute(select(Tenant.id))
        return [str(r[0]) for r in rows.all() if r and r[0]]


async def run_monthly_zus_workspace_for_tenant(
    *,
    tenant_id: str,
    period_yyyy_mm: str,
    dry_run: bool = False,
    actor_id: str | None = None,
) -> dict[str, Any]:
    tid = str(tenant_id).strip()
    act = (actor_id or default_monthly_actor_id()).strip()
    employees_considered = 0
    tasks_created = 0
    would_create = 0

    async with tenant_enforced_session(UUID(tid), actor_id=act) as db:
        eids = (
            (
                await db.execute(
                    select(WorkforceEmployee.id).where(
                        WorkforceEmployee.tenant_id == tid,
                        WorkforceEmployee.status.in_(_MONTHLY_EMPLOYEE_STATUSES),
                    )
                )
            )
            .scalars()
            .all()
        )
        for eid in eids:
            eid_s = str(eid).strip()
            if not eid_s:
                continue
            employees_considered += 1
            if dry_run:
                if await ensure_zus_monthly_settlement_task(
                    db, tid, eid_s, period_yyyy_mm, dry_run=True, actor_id=None
                ):
                    would_create += 1
            else:
                if await ensure_zus_monthly_settlement_task(
                    db, tid, eid_s, period_yyyy_mm, dry_run=False, actor_id=None
                ):
                    tasks_created += 1
        if not dry_run:
            await db.commit()

    logger.info(
        "zus_workspace_monthly tenant_id=%s period=%s dry_run=%s employees=%s created=%s would_create=%s",
        tid,
        period_yyyy_mm,
        dry_run,
        employees_considered,
        tasks_created,
        would_create,
    )
    return {
        "tenant_id": tid,
        "period": period_yyyy_mm,
        "dry_run": dry_run,
        "employees_considered": employees_considered,
        "tasks_created": tasks_created if not dry_run else 0,
        "would_create": would_create if dry_run else 0,
    }


async def run_monthly_zus_workspace_all_tenants(
    *,
    period_yyyy_mm: str,
    tenant_id: str | None = None,
    dry_run: bool = False,
    actor_id: str | None = None,
) -> dict[str, Any]:
    tids = await list_tenant_ids_for_monthly(tenant_id=tenant_id)
    per_tenant: list[dict[str, Any]] = []
    total_created = 0
    total_would = 0
    for tid in tids:
        one = await run_monthly_zus_workspace_for_tenant(
            tenant_id=tid,
            period_yyyy_mm=period_yyyy_mm,
            dry_run=dry_run,
            actor_id=actor_id,
        )
        per_tenant.append(one)
        total_created += int(one.get("tasks_created") or 0)
        total_would += int(one.get("would_create") or 0)
    return {
        "tenants": len(tids),
        "period": period_yyyy_mm,
        "dry_run": dry_run,
        "total_tasks_created": total_created,
        "total_would_create": total_would,
        "per_tenant": per_tenant,
    }
