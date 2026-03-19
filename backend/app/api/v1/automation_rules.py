"""Minimal automation rules builder API (v1)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.automation_rule import AutomationRule
from backend.app.services.automation_rules import TRIGGERS


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
    title: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class AutomationRuleCreateIn(BaseModel):
    enabled: bool = True
    trigger: str = Field(description="One of supported triggers.")
    title: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None


class AutomationRulePatchIn(BaseModel):
    enabled: Optional[bool] = None
    title: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None


class AutomationRuleListOut(BaseModel):
    items: List[AutomationRuleOut]


@router.get(
    "",
    response_model=AutomationRuleListOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.superadmin, Role.supervisor, Role.manager, Role.admin))],
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
    dependencies=[Depends(require_roles(Role.administrator, Role.superadmin, Role.supervisor, Role.manager, Role.admin))],
)
async def create_rule(
    body: AutomationRuleCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    if body.trigger not in TRIGGERS:
        raise HTTPException(status_code=422, detail=f"Unsupported trigger. Allowed: {sorted(TRIGGERS)}")
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    rule = AutomationRule(
        tenant_id=tenant_id,
        enabled=bool(body.enabled),
        trigger=body.trigger,
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
        title=rule.title,
        conditions=_loads(rule.conditions_json),
        actions=_loads(rule.actions_json),
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.patch(
    "/{rule_id}",
    response_model=AutomationRuleOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.superadmin, Role.supervisor, Role.manager, Role.admin))],
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
    if body.enabled is not None:
        rule.enabled = bool(body.enabled)
    if body.title is not None:
        rule.title = body.title
    if body.conditions is not None:
        rule.conditions_json = _dumps(body.conditions)
    if body.actions is not None:
        rule.actions_json = _dumps(body.actions)
    await db.commit()
    await db.refresh(rule)
    return AutomationRuleOut(
        id=rule.id,
        tenant_id=rule.tenant_id,
        enabled=bool(rule.enabled),
        trigger=rule.trigger,
        title=rule.title,
        conditions=_loads(rule.conditions_json),
        actions=_loads(rule.actions_json),
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.administrator, Role.superadmin, Role.supervisor, Role.manager, Role.admin))],
)
async def delete_rule(
    rule_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    row = await db.execute(select(AutomationRule).where(AutomationRule.tenant_id == tenant_id, AutomationRule.id == rule_id))
    rule = row.scalar_one_or_none()
    if not rule:
        return
    await db.delete(rule)
    await db.commit()
    return None

