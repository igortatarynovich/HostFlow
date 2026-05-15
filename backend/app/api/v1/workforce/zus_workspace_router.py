"""ZUS workspace MVP — operational task queue (no ZUS API)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.zus_workspace import (
    ZusWorkspaceTaskCreate,
    ZusWorkspaceTaskOut,
    ZusWorkspaceTaskPageOut,
    ZusWorkspaceTaskPatch,
)
from backend.app.services.audit import log_activity
from backend.app.services import workforce_zus_workspace as zus_svc

router = APIRouter()

HR_WORKSPACE_ROLES = (Role.hr_officer, Role.administrator, Role.supervisor)


@router.get(
    "/tasks",
    response_model=ZusWorkspaceTaskPageOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def list_zus_workspace_tasks(
    status: Optional[str] = Query(None, max_length=32),
    workspace_lane: Optional[str] = Query(None, max_length=32),
    task_kind: Optional[str] = Query(None, max_length=64),
    form_kind: Optional[str] = Query(None, max_length=32),
    due_before: Optional[datetime] = Query(None),
    due_after: Optional[datetime] = Query(None),
    assigned_hr_user_id: Optional[str] = Query(None, max_length=36),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> ZusWorkspaceTaskPageOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    rows, total = await zus_svc.list_zus_workspace_tasks(
        db,
        tenant_id,
        status=status,
        workspace_lane=workspace_lane,
        task_kind=task_kind,
        form_kind=form_kind,
        due_before=due_before,
        due_after=due_after,
        assigned_hr_user_id=assigned_hr_user_id,
        limit=limit,
        offset=offset,
    )
    items = [
        ZusWorkspaceTaskOut.model_validate(
            zus_svc.task_to_out(entry["task"], entry.get("employee_display_name") or "")
        )
        for entry in rows
    ]
    return ZusWorkspaceTaskPageOut(items=items, total=total)


@router.post(
    "/tasks",
    response_model=ZusWorkspaceTaskOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def create_zus_workspace_task(
    payload: ZusWorkspaceTaskCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ZusWorkspaceTaskOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    row = await zus_svc.create_zus_workspace_task(db, tenant_id, payload.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=400, detail="Employee not found for tenant")
    pair = await zus_svc.get_task_with_employee_name(db, tenant_id, row.id)
    if not pair:
        raise HTTPException(status_code=500, detail="Task persisted but could not be reloaded")
    task, dn = pair
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.zus_workspace_task_create",
        actor_id=current_user.sub,
        target_type="workforce_zus_workspace_task",
        target_id=task.id,
        payload={"employee_id": task.employee_id, "workspace_lane": task.workspace_lane},
    )
    await db.commit()
    await db.refresh(task)
    return ZusWorkspaceTaskOut.model_validate(zus_svc.task_to_out(task, dn))


@router.patch(
    "/tasks/{task_id}",
    response_model=ZusWorkspaceTaskOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_zus_workspace_task(
    task_id: str,
    payload: ZusWorkspaceTaskPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ZusWorkspaceTaskOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await zus_svc.patch_zus_workspace_task(db, tenant_id, task_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    pair = await zus_svc.get_task_with_employee_name(db, tenant_id, row.id)
    if not pair:
        raise HTTPException(status_code=404, detail="Task not found")
    task, dn = pair
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.zus_workspace_task_patch",
        actor_id=current_user.sub,
        target_type="workforce_zus_workspace_task",
        target_id=task.id,
        payload={"fields": sorted(data.keys())},
    )
    await db.commit()
    await db.refresh(task)
    return ZusWorkspaceTaskOut.model_validate(zus_svc.task_to_out(task, dn))
