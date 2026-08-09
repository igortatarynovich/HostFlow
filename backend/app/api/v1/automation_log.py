"""Automation log API - explainable automation events based on ActivityLog."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.audit import ActivityLog


def _parse_dt(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if end_of_day and dt.hour == 0 and dt.minute == 0:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except Exception:
        try:
            dt = datetime.fromisoformat(value + "T00:00:00")
            if end_of_day:
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        except Exception:
            return None


class AutomationLogEntryOut(BaseModel):
    id: str
    tenant_id: str
    actor_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime


class AutomationLogListOut(BaseModel):
    items: List[AutomationLogEntryOut]
    total: int


router = APIRouter(prefix="/automation-log", tags=["automation-log"])


@router.get(
    "",
    response_model=AutomationLogListOut,
    dependencies=[Depends(require_trust_write())],
)
async def list_automation_log(
    target_type: Optional[str] = Query(None, description="Filter by target_type (e.g. candidate, lead, document)."),
    target_id: Optional[str] = Query(None, description="Filter by target_id (entity id)."),
    action_prefix: Optional[str] = Query("automation.", description="Only actions starting with this prefix."),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)

    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    stmt = select(ActivityLog).where(ActivityLog.tenant_id == tenant_id)
    count_stmt = select(func.count()).select_from(ActivityLog).where(ActivityLog.tenant_id == tenant_id)

    if action_prefix:
        like = f"{action_prefix}%"
        stmt = stmt.where(ActivityLog.action.like(like))
        count_stmt = count_stmt.where(ActivityLog.action.like(like))
    if target_type:
        stmt = stmt.where(ActivityLog.target_type == target_type)
        count_stmt = count_stmt.where(ActivityLog.target_type == target_type)
    if target_id:
        stmt = stmt.where(ActivityLog.target_id == target_id)
        count_stmt = count_stmt.where(ActivityLog.target_id == target_id)
    if dfrom:
        stmt = stmt.where(ActivityLog.created_at >= dfrom)
        count_stmt = count_stmt.where(ActivityLog.created_at >= dfrom)
    if dto:
        stmt = stmt.where(ActivityLog.created_at <= dto)
        count_stmt = count_stmt.where(ActivityLog.created_at <= dto)

    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = await db.execute(stmt.order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit))
    logs = list(rows.scalars().all())
    return AutomationLogListOut(
        items=[
            AutomationLogEntryOut(
                id=log.id,
                tenant_id=log.tenant_id,
                actor_id=log.actor_id,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                payload=log.payload,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
    )

