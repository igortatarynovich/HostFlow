from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import ActivityLog
from backend.app.models.automation_rule import AutomationRule
from backend.app.services.audit import log_activity
from backend.app.services import reminder_tasks
from backend.app.services.plan_feature_gates import (
    TRIAL_AUTOMATION_RUNS_METRIC,
    enforce_trial_usage_cap_and_increment,
)


TRIGGERS = {
    "candidate.created",
    "candidate.stage_changed",
    "candidate.risk_band",
    "document.expiring",
    "lead.processed",
    "lead.pipeline.stage_changed",
}

RISK_BAND_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def risk_band_at_least(band: str, min_band: str) -> bool:
    br = RISK_BAND_ORDER.get(str(band).strip().lower(), -1)
    mr = RISK_BAND_ORDER.get(str(min_band).strip().lower(), 2)
    return br >= mr


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


_MISSING = object()


def _get_at_path(ctx: Any, path: str) -> Any:
    """Return value at dot path or _MISSING if any segment is absent."""
    cur: Any = ctx
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return _MISSING
    return cur


def _source_str_equal(cur: Any, expected: Any) -> bool:
    return str(cur or "").strip().lower() == str(expected or "").strip().lower()


def _scalar_equal_for_path(path: str, cur: Any, expected: Any) -> bool:
    if path == "source":
        return _source_str_equal(cur, expected)
    return str(cur) == str(expected)


def _match_operator(path: str, cur: Any, spec: dict, *, missing: bool) -> bool:
    op = str(spec.get("op") or "").strip().lower()
    if op in ("eq", "=="):
        if missing:
            return False
        val = spec.get("value", spec.get("v"))
        return _scalar_equal_for_path(path, cur, val)
    if op in ("neq", "!=", "<>"):
        if missing:
            return True
        val = spec.get("value", spec.get("v"))
        return not _scalar_equal_for_path(path, cur, val)
    if op == "in":
        if missing:
            return False
        raw = spec.get("value", spec.get("values"))
        if not isinstance(raw, list):
            return False
        if path == "source":
            c = str(cur or "").strip().lower()
            opts = [str(x or "").strip().lower() for x in raw]
            return c in opts
        sc = str(cur)
        return sc in [str(x) for x in raw]
    if op == "exists":
        if missing:
            return False
        if cur is None:
            return False
        if isinstance(cur, str) and not str(cur).strip():
            return False
        return True
    if op in ("not_exists", "missing"):
        if missing:
            return True
        if cur is None:
            return True
        if isinstance(cur, str) and not str(cur).strip():
            return True
        return False
    return False


def _match_condition_key(path: str, expected: Any, ctx: dict) -> bool:
    cur = _get_at_path(ctx, path)
    missing = cur is _MISSING
    if isinstance(expected, dict) and str(expected.get("op") or "").strip():
        return _match_operator(path, cur, expected, missing=missing)
    if isinstance(expected, dict):
        eff_cur = None if missing else cur
        return str(eff_cur) == str(expected)
    if expected is None:
        eff = None if missing else cur
        return eff is None
    eff_cur = None if missing else cur
    return _scalar_equal_for_path(path, eff_cur, expected)


def _matches_conditions(conditions: dict, ctx: dict) -> bool:
    """
    Match rule conditions against context (implicit AND on all clauses).

    - Dot paths: ``normalized.country``, ``stage``, etc.
    - Legacy: scalar value → equality (``source`` compared case-insensitively).
    - ``null`` / missing JSON null → value at path must be null / missing.
    - Operator object: ``{"op": "eq"|"neq"|"in"|"exists"|"not_exists", "value": ...}``
      (aliases ``==``, ``!=``, ``<>``, ``missing``).
    - ``$and``: list of nested condition dicts; each must match (recursive).
    """
    if not conditions:
        return True
    if not isinstance(conditions, dict):
        return False
    and_list = conditions.get("$and")
    if and_list is not None:
        if not isinstance(and_list, list):
            return False
        for sub in and_list:
            if not isinstance(sub, dict):
                return False
            if not _matches_conditions(sub, ctx):
                return False
    for key, expected in conditions.items():
        if key == "$and":
            continue
        if key is None:
            continue
        if not _match_condition_key(str(key), expected, ctx):
            return False
    return True


async def list_rules(db: AsyncSession, *, tenant_id: str, trigger: Optional[str] = None) -> List[AutomationRule]:
    stmt = select(AutomationRule).where(AutomationRule.tenant_id == tenant_id)
    if trigger:
        stmt = stmt.where(AutomationRule.trigger == trigger)
    rows = await db.execute(stmt.order_by(AutomationRule.created_at.desc()))
    return list(rows.scalars().all())


async def was_rule_fired_for_candidate_since(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
    candidate_id: str,
    trigger: str,
    since: datetime,
) -> bool:
    """Dedupe hourly risk (and similar) automations: same rule + candidate + trigger within window."""
    rows = (
        await db.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "automation.rule_fired",
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == candidate_id,
                ActivityLog.created_at >= since,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(48)
        )
    ).all()
    for (payload,) in rows:
        p = payload if isinstance(payload, dict) else {}
        if str(p.get("trigger") or "") != trigger:
            continue
        if str(p.get("rule_id") or "") == str(rule_id):
            return True
    return False


async def execute_automation_rule(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule: AutomationRule,
    trigger: str,
    actor_id: Optional[str],
    context: Dict[str, Any],
) -> None:
    """Run one matched rule (log + optional create_reminder)."""
    conditions = _loads_or_empty(rule.conditions_json)
    actions = _loads_or_empty(rule.actions_json)
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


async def run_candidate_risk_band_rules(
    db: AsyncSession,
    *,
    tenant_id: str,
    shadow_rows: Sequence[dict[str, Any]],
    assignee_by_candidate_id: Dict[str, Optional[str]],
    dedupe_hours: int = 24,
    min_band: str = "high",
) -> dict[str, int]:
    """
    Phase D: fire `candidate.risk_band` automation rules for hourly high/critical shadow rows.
    Requires assignee (manager/recruiter) on the candidate; skips rows without owner.
    """
    trigger = "candidate.risk_band"
    rows = await db.execute(
        select(AutomationRule).where(
            AutomationRule.tenant_id == tenant_id,
            AutomationRule.enabled.is_(True),
            AutomationRule.trigger == trigger,
        )
    )
    rules = list(rows.scalars().all())
    if not rules:
        return {"candidates_seen": 0, "rules_fired": 0, "rows_skipped_no_assignee": 0}

    dedupe_h = max(1, min(int(dedupe_hours), 168))
    since = _now() - timedelta(hours=dedupe_h)
    fired = 0
    skipped = 0
    seen = 0

    for raw in shadow_rows:
        cid = str(raw.get("candidate_id") or "").strip()
        if not cid:
            continue
        band = str(raw.get("band") or "").strip().lower()
        if not risk_band_at_least(band, min_band):
            continue
        seen += 1
        assignee = assignee_by_candidate_id.get(cid)
        if not assignee or not str(assignee).strip():
            skipped += 1
            continue
        assignee_s = str(assignee).strip()
        score = raw.get("score")
        ctx: Dict[str, Any] = {
            "entity_type": "candidate",
            "entity_id": cid,
            "risk_band": band,
            "risk_score": "" if score is None else str(score),
            "stage": str(raw.get("stage_at_score") or ""),
            "assignee_id": assignee_s,
        }
        for rule in rules:
            conditions = _loads_or_empty(rule.conditions_json)
            if not _matches_conditions(conditions, ctx):
                continue
            if await was_rule_fired_for_candidate_since(
                db,
                tenant_id=tenant_id,
                rule_id=str(rule.id),
                candidate_id=cid,
                trigger=trigger,
                since=since,
            ):
                continue
            await enforce_trial_usage_cap_and_increment(
                db,
                tenant_id=tenant_id,
                metric=TRIAL_AUTOMATION_RUNS_METRIC,
                increment=1,
            )
            await execute_automation_rule(
                db,
                tenant_id=tenant_id,
                rule=rule,
                trigger=trigger,
                actor_id=assignee_s,
                context=ctx,
            )
            fired += 1

    return {
        "candidates_seen": seen,
        "rules_fired": fired,
        "rows_skipped_no_assignee": skipped,
    }


async def run_rules(
    db: AsyncSession,
    *,
    tenant_id: str,
    trigger: str,
    actor_id: Optional[str],
    context: Dict[str, Any],
) -> int:
    """Execute enabled rules for trigger. Action v1: create_reminder."""
    # §2.10: `lead.qualification` is evaluated only inside lead ingest (not here).
    if trigger == "lead.qualification":
        return 0
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
        if not _matches_conditions(conditions, context):
            continue
        await enforce_trial_usage_cap_and_increment(
            db,
            tenant_id=tenant_id,
            metric=TRIAL_AUTOMATION_RUNS_METRIC,
            increment=1,
        )
        fired += 1
        await execute_automation_rule(
            db,
            tenant_id=tenant_id,
            rule=rule,
            trigger=trigger,
            actor_id=actor_id,
            context=context,
        )
    return fired

