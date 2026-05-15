"""HR operational alerts — worker dispatch (v1).

Uses :func:`tenant_enforced_session` so Postgres RLS + audit actor context match other jobs.
Safe to run on a schedule: ``dispatch_hr_operational_alerts`` is throttled and idempotent.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import tenant_enforced_session
from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant
from backend.app.models.user import Role, User
from backend.app.services.hr_operational_alerts import dispatch_hr_operational_alerts

logger = logging.getLogger(__name__)

_DEFAULT_ACTOR_ID = "system:hr_operational_alerts_dispatch"

_VIEWER_ROLE_PRIORITY: dict[str, int] = {
    Role.superadmin.value: 0,
    Role.administrator.value: 1,
    Role.hr_officer.value: 2,
    Role.supervisor.value: 3,
}

_OPERABLE_ROLES = (
    Role.superadmin,
    Role.administrator,
    Role.hr_officer,
    Role.supervisor,
)


def default_dispatch_actor_id() -> str:
    return (os.environ.get("HR_OPERATIONAL_ALERTS_ACTOR_ID") or _DEFAULT_ACTOR_ID).strip()


def _role_value(role: Role | str) -> str:
    if isinstance(role, Role):
        return str(role.value)
    s = str(role).strip()
    if s.startswith("Role."):
        return s.split(".", 1)[-1].lower()
    return s.lower()


async def resolve_privileged_viewer(
    db: AsyncSession, *, tenant_id: str
) -> tuple[str, str] | None:
    """Pick a synthetic dashboard viewer (team scope) for risk listing: lowest priority index wins."""
    tid = str(tenant_id).strip()
    rows = (
        (
            await db.execute(
                select(User.id, User.role).where(
                    User.tenant_id == tid,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                    User.role.in_(_OPERABLE_ROLES),
                )
            )
        )
        .all()
    )
    if not rows:
        return None
    best_uid: str | None = None
    best_role: str | None = None
    best_pri = 99
    for uid, role in rows:
        rv = _role_value(role)
        pri = _VIEWER_ROLE_PRIORITY.get(rv, 99)
        if pri < best_pri:
            best_pri = pri
            best_uid = str(uid)
            best_role = rv
    if not best_uid or best_role is None:
        return None
    return best_uid, best_role


async def list_tenant_ids_for_dispatch(*, tenant_id: str | None) -> list[str]:
    one = (tenant_id or "").strip()
    if one:
        return [one]
    async with async_session_maker() as db:
        rows = await db.execute(select(Tenant.id))
        return [str(r[0]) for r in rows.all() if r and r[0]]


async def dispatch_hr_operational_alerts_for_tenant(
    *,
    tenant_id: str,
    dry_run: bool = False,
    horizon_days: int = 90,
    assignee_scope: str = "team",
    actor_id: str | None = None,
    viewer_id: str | None = None,
    viewer_role: str | None = None,
) -> dict[str, Any]:
    """Run alert dispatch for one tenant; commits on success."""
    tid = str(tenant_id).strip()
    act = (actor_id or default_dispatch_actor_id()).strip()
    logger.info(
        "hr_operational_alerts_dispatch start tenant_id=%s dry_run=%s actor_id=%s",
        tid,
        dry_run,
        act,
    )
    async with tenant_enforced_session(UUID(tid), actor_id=act) as db:
        if viewer_id and viewer_role:
            vid = str(viewer_id).strip()
            vrole = str(viewer_role).strip().lower()
        else:
            resolved = await resolve_privileged_viewer(db, tenant_id=tid)
            if not resolved:
                logger.warning(
                    "hr_operational_alerts_dispatch skipped tenant_id=%s reason=no_privileged_user",
                    tid,
                )
                return {
                    "tenant_id": tid,
                    "skipped": True,
                    "reason": "no_privileged_user",
                    "dry_run": dry_run,
                }
            vid, vrole = resolved

        out = await dispatch_hr_operational_alerts(
            db,
            tenant_id=tid,
            viewer_id=vid,
            viewer_role=vrole,
            assignee_scope=assignee_scope,
            horizon_days=horizon_days,
            dry_run=dry_run,
            actor_id=act,
        )
        await db.commit()

    logger.info(
        "hr_operational_alerts_dispatch end tenant_id=%s dry_run=%s risk_items_examined=%s "
        "notifications_returned=%s suppressed_pre_check=%s audit_rows_written=%s would_notify_slots=%s",
        tid,
        dry_run,
        out.get("risk_items_examined"),
        out.get("notifications_returned"),
        out.get("suppressed_pre_check"),
        out.get("audit_rows_written"),
        out.get("would_notify_slots"),
    )
    return {"tenant_id": tid, **out}


async def dispatch_hr_operational_alerts_all_tenants(
    *,
    tenant_id: str | None = None,
    dry_run: bool = False,
    horizon_days: int = 90,
    assignee_scope: str = "team",
    actor_id: str | None = None,
    viewer_id: str | None = None,
    viewer_role: str | None = None,
) -> dict[str, Any]:
    """Iterate tenants (or one if ``tenant_id`` set); each tenant uses its own RLS-bound session."""
    tids = await list_tenant_ids_for_dispatch(tenant_id=tenant_id)
    per_tenant: list[dict[str, Any]] = []
    skipped = 0
    processed = 0
    totals = {
        "risk_items_examined": 0,
        "notifications_returned": 0,
        "suppressed_pre_check": 0,
        "audit_rows_written": 0,
        "would_notify_slots": 0,
    }
    for tid in tids:
        one = await dispatch_hr_operational_alerts_for_tenant(
            tenant_id=tid,
            dry_run=dry_run,
            horizon_days=horizon_days,
            assignee_scope=assignee_scope,
            actor_id=actor_id,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
        )
        per_tenant.append(one)
        if one.get("skipped"):
            skipped += 1
        else:
            processed += 1
            for k in totals:
                totals[k] += int(one.get(k) or 0)

    summary = {
        "tenants_considered": len(tids),
        "tenants_skipped": skipped,
        "tenants_processed": processed,
        "dry_run": dry_run,
        **{f"total_{k}": v for k, v in totals.items()},
        "per_tenant": per_tenant,
    }
    logger.info(
        "hr_operational_alerts_dispatch batch_complete tenants_considered=%s "
        "tenants_processed=%s tenants_skipped=%s dry_run=%s total_notifications_returned=%s",
        summary["tenants_considered"],
        summary["tenants_processed"],
        summary["tenants_skipped"],
        dry_run,
        summary["total_notifications_returned"],
    )
    return summary
