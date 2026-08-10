"""Minimal automation rules builder API (v1)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.automation_rule import AutomationRule
from backend.app.services import billing_restrictions
from backend.app.services.automation_rules import TRIGGERS
from backend.app.services.plan_feature_gates import (
    ensure_automation_rules_enabled_count_allows_transition,
    ensure_automation_rules_mutation_allowed,
)

# Triggers stored in DB; `lead.qualification` runs only in lead ingest (see lead_qualification_rules).
ALLOWED_RULE_TRIGGERS = set(TRIGGERS) | {"lead.qualification"}


router = APIRouter(prefix="/automation-rules", tags=["automation-rules"])
logger = logging.getLogger(__name__)


def _is_missing_table_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "no such table: automation_rules" in msg
        or "relation \"automation_rules\" does not exist" in msg
        or "undefined table" in msg
    )


def _dumps(obj: Optional[dict]) -> Optional[str]:
    if obj is None:
        return None
    return json.dumps(obj)


def _loads(raw: Optional[str]) -> Optional[dict]:
    if raw is None:
        return None
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else None
    except Exception:
        return None


class AutomationRuleOut(BaseModel):
    id: str
    tenant_id: str
    enabled: bool
    trigger: str
    priority: int = 0
    title: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class AutomationRuleCreateIn(BaseModel):
    enabled: bool = True
    trigger: str = Field(description="One of supported triggers.")
    priority: int = Field(default=0, ge=0, le=1_000_000)
    title: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None


class AutomationRulePatchIn(BaseModel):
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    title: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None


class AutomationRuleListOut(BaseModel):
    items: List[AutomationRuleOut]


_LQ_CONDITION_OPS = frozenset(
    {"eq", "==", "neq", "!=", "<>", "in", "exists", "not_exists", "missing"}
)


def _validate_lead_qualification_conditions(cond: Any, *, depth: int = 0) -> None:
    if depth > 16:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lead.qualification conditions: nesting too deep",
        )
    if not isinstance(cond, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lead.qualification conditions must be a JSON object",
        )
    if len(cond) > 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lead.qualification conditions: too many keys",
        )
    for k in cond:
        if isinstance(k, str) and k.startswith("$") and k != "$and":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lead.qualification conditions: only reserved key is $and",
            )
    and_list = cond.get("$and")
    if and_list is not None:
        if not isinstance(and_list, list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lead.qualification $and must be a JSON array",
            )
        if len(and_list) > 32:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lead.qualification $and: too many clauses",
            )
        for item in and_list:
            _validate_lead_qualification_conditions(item, depth=depth + 1)
    for key, val in cond.items():
        if key == "$and":
            continue
        if key is None or (isinstance(key, str) and not str(key).strip()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lead.qualification conditions: empty path key",
            )
        if isinstance(val, dict) and str(val.get("op") or "").strip():
            op = str(val.get("op")).strip().lower()
            if op not in _LQ_CONDITION_OPS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"lead.qualification conditions: unsupported op {op!r}",
                )
            if op == "in":
                raw = val.get("value", val.get("values"))
                if not isinstance(raw, list) or len(raw) > 256:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="lead.qualification 'in' expects value as JSON array (max 256 items)",
                    )
            if op in ("eq", "==", "neq", "!=", "<>"):
                if "value" not in val and "v" not in val:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"lead.qualification op {op!r} requires value",
                    )


def _validate_rule_payload(*, trigger: str, conditions: Optional[dict], actions: Optional[dict]) -> None:
    if trigger != "lead.qualification":
        return
    cond = conditions if isinstance(conditions, dict) else {}
    _validate_lead_qualification_conditions(cond)
    act = actions if isinstance(actions, dict) else {}
    vid = str(act.get("set_vacancy_id") or "").strip()
    if not vid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lead.qualification rules require actions.set_vacancy_id (vacancy UUID)",
        )
    try:
        UUID(vid)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="actions.set_vacancy_id must be a valid UUID",
        ) from exc
    rid = str(act.get("set_recruiter_id") or "").strip()
    if rid:
        try:
            UUID(rid)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="actions.set_recruiter_id must be a valid UUID",
            ) from exc


@router.get(
    "",
    response_model=AutomationRuleListOut,
    dependencies=[Depends(require_trust_write())],
)
async def list_rules(
    trigger: Optional[str] = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    stmt = select(AutomationRule).where(AutomationRule.tenant_id == tenant_id)
    if trigger:
        stmt = stmt.where(AutomationRule.trigger == trigger)
    try:
        rows = await db.execute(stmt.order_by(AutomationRule.created_at.desc()))
    except (ProgrammingError, OperationalError) as exc:
        # Backward-compatible guard for environments where automation_rules
        # migration did not run yet: keep page usable and surface empty state.
        if _is_missing_table_error(exc):
            logger.warning("[automation-rules] table missing, returning empty list tenant=%s", tenant_id)
            return AutomationRuleListOut(items=[])
        raise
    items = []
    for r in rows.scalars().all():
        items.append(
            AutomationRuleOut(
                id=r.id,
                tenant_id=r.tenant_id,
                enabled=bool(r.enabled),
                trigger=r.trigger,
                priority=int(getattr(r, "priority", 0) or 0),
                title=r.title,
                conditions=_loads(r.conditions_json),
                actions=_loads(r.actions_json),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return AutomationRuleListOut(items=items)


@router.post(
    "",
    response_model=AutomationRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trust_write())],
)
async def create_rule(
    body: AutomationRuleCreateIn,
    _ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    if body.trigger not in ALLOWED_RULE_TRIGGERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported trigger. Allowed: {sorted(ALLOWED_RULE_TRIGGERS)}",
        )
    _validate_rule_payload(trigger=body.trigger, conditions=body.conditions, actions=body.actions)
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id)
    await ensure_automation_rules_mutation_allowed(db, tenant_id)
    await ensure_automation_rules_enabled_count_allows_transition(
        db,
        tenant_id,
        was_enabled=False,
        will_be_enabled=bool(body.enabled),
    )
    rule = AutomationRule(
        tenant_id=tenant_id,
        enabled=bool(body.enabled),
        trigger=body.trigger,
        priority=int(body.priority),
        title=body.title,
        conditions_json=_dumps(body.conditions),
        actions_json=_dumps(body.actions),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return AutomationRuleOut(
        id=rule.id,
        tenant_id=rule.tenant_id,
        enabled=bool(rule.enabled),
        trigger=rule.trigger,
        priority=int(getattr(rule, "priority", 0) or 0),
        title=rule.title,
        conditions=_loads(rule.conditions_json),
        actions=_loads(rule.actions_json),
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.patch(
    "/{rule_id}",
    response_model=AutomationRuleOut,
    dependencies=[Depends(require_trust_write())],
)
async def patch_rule(
    rule_id: str,
    body: AutomationRulePatchIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    row = await db.execute(select(AutomationRule).where(AutomationRule.tenant_id == tenant_id, AutomationRule.id == rule_id))
    rule = row.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    only_disable = (
        body.enabled is False
        and body.title is None
        and body.priority is None
        and body.conditions is None
        and body.actions is None
    )
    if not only_disable:
        await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id)
        await ensure_automation_rules_mutation_allowed(db, tenant_id)
    if body.enabled is not None:
        await ensure_automation_rules_enabled_count_allows_transition(
            db,
            tenant_id,
            was_enabled=bool(rule.enabled),
            will_be_enabled=bool(body.enabled),
        )
        rule.enabled = bool(body.enabled)
    if body.priority is not None:
        rule.priority = int(body.priority)
    if body.title is not None:
        rule.title = body.title
    if body.conditions is not None:
        rule.conditions_json = _dumps(body.conditions)
    if body.actions is not None:
        rule.actions_json = _dumps(body.actions)
    if body.conditions is not None or body.actions is not None or body.priority is not None:
        _validate_rule_payload(
            trigger=rule.trigger,
            conditions=_loads(rule.conditions_json),
            actions=_loads(rule.actions_json),
        )
    await db.commit()
    await db.refresh(rule)
    return AutomationRuleOut(
        id=rule.id,
        tenant_id=rule.tenant_id,
        enabled=bool(rule.enabled),
        trigger=rule.trigger,
        priority=int(getattr(rule, "priority", 0) or 0),
        title=rule.title,
        conditions=_loads(rule.conditions_json),
        actions=_loads(rule.actions_json),
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
    dependencies=[Depends(require_trust_write())],
)
async def delete_rule(
    rule_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id)
    row = await db.execute(select(AutomationRule).where(AutomationRule.tenant_id == tenant_id, AutomationRule.id == rule_id))
    rule = row.scalar_one_or_none()
    if not rule:
        return
    await db.delete(rule)
    await db.commit()
    return None

