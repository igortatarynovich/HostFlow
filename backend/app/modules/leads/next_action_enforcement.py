"""Tenant next-action enforcement before CRM stage changes on leads."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Reminder, Tenant
from backend.app.models.reminder import ReminderStatus


async def get_next_action_enforcement_mode(db: AsyncSession, *, tenant_id: str) -> str:
    """Return normalized mode: '', 'off', 'warn', or 'block'."""
    try:
        row = (await db.execute(select(Tenant.settings).where(Tenant.id == tenant_id).limit(1))).first()
        settings_payload = row[0] if row else {}
        settings_dict = settings_payload if isinstance(settings_payload, dict) else {}
    except Exception:
        settings_dict = {}
    enforcement = settings_dict.get("next_action_enforcement_v1") if isinstance(settings_dict, dict) else None
    enforcement_mode = ""
    if isinstance(enforcement, dict):
        enforcement_mode = str(enforcement.get("mode") or "").strip().lower()
    elif isinstance(enforcement, str):
        enforcement_mode = enforcement.strip().lower()
    return enforcement_mode


async def lead_has_active_next_action_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> bool:
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    return bool(
        (
            await db.execute(
                select(
                    exists().where(
                        Reminder.tenant_id == tenant_id,
                        Reminder.entity_type == "lead",
                        Reminder.entity_id == str(lead_id),
                        Reminder.status.in_(active_statuses),
                    )
                )
            )
        ).scalar_one()
    )


async def maybe_log_missing_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: Optional[str],
    lead_id: str,
    attempted_stage: Any,
    mode: str,
) -> None:
    from backend.app.services.audit import log_activity

    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="analytics.next_action.missing",
            target_type="lead",
            target_id=str(lead_id),
            payload={
                "entity_type": "lead",
                "entity_id": str(lead_id),
                "attempted_stage": attempted_stage,
                "mode": mode,
            },
        )
    except Exception:
        pass
