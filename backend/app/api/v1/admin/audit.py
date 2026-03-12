"""Admin audit log API - tenant-wide audit events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.services import users as users_service


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


class AuditEntryOut(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str] = None
    user_label: str = ""
    actor_id: Optional[str] = None
    actor_label: str = ""
    action: str
    payload: Optional[dict[str, Any]] = None
    created_at: datetime


class AuditListOut(BaseModel):
    items: List[AuditEntryOut]
    total: int


router = APIRouter(
    prefix="/admin/audit",
    tags=["admin-audit"],
)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    if (ctx.role or "").strip().lower() == Role.superadmin.value:
        return
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


@router.get(
    "",
    response_model=AuditListOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.superadmin))],
)
async def list_audit(
    user_id: Optional[str] = Query(None, description="Filter by user (subject)"),
    action: Optional[str] = Query(None, description="Filter by action"),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    """List tenant-wide audit log with optional filters."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)

    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    items, total = await users_service.list_tenant_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        date_from=dfrom,
        date_to=dto,
        limit=limit,
        offset=offset,
    )
    return AuditListOut(
        items=[AuditEntryOut(**item) for item in items],
        total=total,
    )
