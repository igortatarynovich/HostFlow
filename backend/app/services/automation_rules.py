from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.automation_rule import AutomationRule
from backend.app.services.audit import log_activity
from backend.app.services import reminder_tasks


TRIGGERS = {
    "candidate.created",
    "candidate.stage_changed",
    "document.expiring",
    "lead.processed",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _loads_or_empty(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {}
    except Exception:
        return {}


def _matches_conditions(conditions: dict, ctx: dict) -> bool:
    """Minimal matcher: equality for top-level keys, supports nested 'ctx.<key>' via dot paths."""
    if not conditions:
        return True
    for key, expected in conditions.items():
        if key is None:
            continue
        path = str(key)
        cur: Any = ctx
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                cur = None
                break
        if expected is None:
            if cur is not None:
                return False
        else:
            if str(cur) != str(expected):
                return False
    return True


async def list_rules(db: AsyncSession, *, tenant_id: str, trigger: Optional[str] = None) -> List[AutomationRule]:
    stmt = select(AutomationRule).where(AutomationRule.tenant_id == tenant_id)
    if trigger:
        stmt = stmt.where(AutomationRule.trigger == trigger)
    rows = await db.execute(stmt.order_by(AutomationRule.created_at.desc()))
    return list(rows.scalars().all())


async def run_rules(
    db: AsyncSession,
    *,
    tenant_id: str,
    trigger: str,
    actor_id: Optional[str],
    context: Dict[str, Any],
) -> int:
    """Execute enabled rules for trigger. Action v1: create_reminder."""
    if trigger not in TRIGGERS:
        return 0
    rows = await db.execute(
        select(AutomationRule).where(
            AutomationRule.tenant_id == tenant_id,
            AutomationRule.enabled.is_(True),
            AutomationRule.trigger == trigger,
        )
    )
    rules = list(rows.scalars().all())
    fired = 0
    for rule in rules:
        conditions = _loads_or_empty(rule.conditions_json)
        actions = _loads_or_empty(rule.actions_json)
        if not _matches_conditions(conditions, context):
            continue
        fired += 1
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="automation.rule_fired",
            target_type=str(context.get("entity_type") or ""),
            target_id=str(context.get("entity_id") or ""),
            payload={"rule_id": rule.id, "trigger": trigger, "title": rule.title, "conditions": conditions},
        )
        reminder_action = actions.get("create_reminder") if isinstance(actions, dict) else None
        if isinstance(reminder_action, dict):
            entity_type = str(reminder_action.get("entity_type") or context.get("entity_type") or "custom")
            entity_id = str(reminder_action.get("entity_id") or context.get("entity_id") or "")
            title = str(reminder_action.get("title") or rule.title or "Follow up").strip()
            assignee_id = str(reminder_action.get("assignee_id") or context.get("assignee_id") or actor_id or "").strip()
            if not assignee_id:
                assignee_id = str(actor_id or "")
            due_in_minutes = int(reminder_action.get("due_in_minutes") or 60)
            due_at = _now() + timedelta(minutes=max(0, due_in_minutes))
            await reminder_tasks.create_reminder(
                db,
                tenant_id=tenant_id,
                actor_id=assignee_id or (actor_id or assignee_id),
                payload={
                    "title": title,
                    "type": "custom",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "assignee_id": assignee_id or None,
                    "priority": reminder_action.get("priority") or "normal",
                    "channel": "internal",
                    "due_at": due_at,
                    "payload": {"source": "automation_rules", "rule_id": rule.id, "trigger": trigger, **(context or {})},
                },
            )
            await log_activity(
                db,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="automation.action.create_reminder",
                target_type=entity_type,
                target_id=entity_id,
                payload={"rule_id": rule.id, "title": title, "due_at": due_at.isoformat()},
            )
    return fired

