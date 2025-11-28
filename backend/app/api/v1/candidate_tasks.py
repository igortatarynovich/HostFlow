from __future__ import annotations

import json
import uuid
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles, get_current_user, UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate_children import CandidateTask
from backend.app.api.v1.candidates.acl import ensure_candidate_access


router = APIRouter(prefix="/candidates", tags=["candidate-tasks"], redirect_slashes=False)

RESTRICTED_ROLES = {
    Role.recruiter.value,
    Role.supervisor.value,
    Role.manager.value,
}


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    status: str = "pending"
    completed: Optional[bool] = False


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    completed: Optional[bool] = None


class TaskOut(BaseModel):
    id: str
    candidate_id: str
    title: str
    description: Optional[str]
    status: str
    due_date: Optional[str]
    priority: Optional[str]
    assigned_to: Optional[str]
    completed: bool


def _task_to_out(row: CandidateTask) -> TaskOut:
    return TaskOut(
        id=row.id,
        candidate_id=row.candidate_id,
        title=row.title,
        description=row.description,
        status=row.status,
        due_date=row.due_on,
        priority=row.priority,
        assigned_to=row.assigned_to,
        completed=bool(row.completed),
    )


@router.post(
    "/{candidate_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.manager, Role.admin, Role.recruiter))],
)
async def create_task(
    candidate_id: uuid.UUID,
    payload: TaskCreate,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    task_id = str(uuid.uuid4())
    completed_flag = 1 if payload.completed else 0
    status_value = payload.status or ("completed" if completed_flag else "pending")
    await db.execute(
        insert(CandidateTask).values(
            id=task_id,
            tenant_id=tenant_str,
            candidate_id=str(candidate_id),
            title=payload.title,
            description=payload.description,
            status=status_value,
            due_on=payload.due_date,
            priority=payload.priority,
            assigned_to=payload.assigned_to,
            completed=completed_flag,
            meta=json.dumps({}, ensure_ascii=False),
        )
    )
    await db.commit()
    row = await db.execute(
        select(CandidateTask).where(
            CandidateTask.id == task_id, CandidateTask.tenant_id == tenant_str
        )
    )
    task = row.scalar_one()
    return _task_to_out(task)


@router.get(
    "/{candidate_id}/tasks",
    response_model=list[TaskOut],
    dependencies=[Depends(require_roles(Role.manager, Role.viewer, Role.admin, Role.recruiter))],
)
async def list_tasks(
    candidate_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    result = await db.execute(
        select(CandidateTask).where(
            CandidateTask.candidate_id == str(candidate_id),
            CandidateTask.tenant_id == tenant_str,
        )
    )
    return [_task_to_out(r) for r in result.scalars().all()]


@router.patch(
    "/{candidate_id}/tasks/{task_id}",
    response_model=TaskOut,
    dependencies=[Depends(require_roles(Role.manager, Role.admin, Role.recruiter))],
)
async def update_task(
    candidate_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    result = await db.execute(
        select(CandidateTask).where(
            CandidateTask.id == str(task_id),
            CandidateTask.candidate_id == str(candidate_id),
            CandidateTask.tenant_id == tenant_str,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    changes = {}
    if payload.title is not None:
        changes["title"] = payload.title
    if payload.description is not None:
        changes["description"] = payload.description
    if payload.status is not None:
        changes["status"] = payload.status
    if payload.due_date is not None:
        changes["due_on"] = payload.due_date
    if payload.priority is not None:
        changes["priority"] = payload.priority
    if payload.assigned_to is not None:
        changes["assigned_to"] = payload.assigned_to
    if payload.completed is not None:
        changes["completed"] = 1 if payload.completed else 0
        if payload.status is None:
            changes["status"] = "completed" if payload.completed else "pending"
    # meta field unused for now

    if changes:
        changes["updated_at"] = text("CURRENT_TIMESTAMP")
        await db.execute(
            update(CandidateTask)
            .where(
                CandidateTask.id == str(task_id),
                CandidateTask.tenant_id == tenant_str,
            )
            .values(**changes)
        )
        await db.commit()

    result = await db.execute(
        select(CandidateTask).where(
            CandidateTask.id == str(task_id),
            CandidateTask.tenant_id == tenant_str,
        )
    )
    task = result.scalar_one()
    return _task_to_out(task)


@router.delete(
    "/{candidate_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.manager, Role.admin, Role.recruiter))],
)
async def delete_task(
    candidate_id: uuid.UUID,
    task_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    result = await db.execute(
        delete(CandidateTask).where(
            CandidateTask.id == str(task_id),
            CandidateTask.candidate_id == str(candidate_id),
            CandidateTask.tenant_id == tenant_str,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.commit()
