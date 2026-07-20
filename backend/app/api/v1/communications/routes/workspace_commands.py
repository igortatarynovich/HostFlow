"""C1.2 — Workspace Command HTTP surface.

POST /communications/threads/{thread_id}/commands/{command}

Every success returns ThreadContext (not bare ThreadOut).
"""

from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.communications.workspace_commands import (
    WorkspaceCommandError,
    assign_thread,
    mark_thread_read,
    mark_thread_unread,
    unassign_thread,
)
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.communications_access import assert_comm_feature_access

from .._helpers.access import (
    _ensure_thread_matches_own_company_scope,
    _feature_for_channel,
    _get_tenant_or_404,
    _get_thread_or_404,
)

router = APIRouter(tags=["communications-workspace-commands"])


class AssignThreadBody(BaseModel):
    assignee_id: str = Field(..., min_length=1, max_length=36)
    reason: str = Field(default="manual", max_length=64)


class UnassignThreadBody(BaseModel):
    reason: str = Field(default="manual", max_length=64)


def _http_command_error(exc: WorkspaceCommandError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def _load_thread_for_command(
    *,
    thread_id: str,
    db_tenant: Tuple[AsyncSession, UUID],
    current_user: UserCtx,
    own_company_id: Optional[str],
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(
        tenant=tenant,
        current_user=current_user,
        tenant_id=tenant_id,
        feature=_feature_for_channel(thread.channel),  # type: ignore[arg-type]
    )
    actor = str(getattr(current_user, "sub", "") or "") or None
    return db, tenant_id, thread, actor


@router.post("/threads/{thread_id}/commands/AssignThread")
async def command_assign_thread(
    thread_id: str,
    body: AssignThreadBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    try:
        result = await assign_thread(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            assignee_id=body.assignee_id,
            reason=body.reason,
            command_id="AssignThread",
        )
    except WorkspaceCommandError as exc:
        raise _http_command_error(exc) from exc
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/ReassignThread")
async def command_reassign_thread(
    thread_id: str,
    body: AssignThreadBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    try:
        result = await assign_thread(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            assignee_id=body.assignee_id,
            reason=body.reason,
            command_id="ReassignThread",
        )
    except WorkspaceCommandError as exc:
        raise _http_command_error(exc) from exc
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/UnassignThread")
async def command_unassign_thread(
    thread_id: str,
    body: UnassignThreadBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    try:
        result = await unassign_thread(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            reason=(body.reason if body else "manual"),
        )
    except WorkspaceCommandError as exc:
        raise _http_command_error(exc) from exc
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/MarkThreadRead")
async def command_mark_thread_read(
    thread_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await mark_thread_read(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor,
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/MarkThreadUnread")
async def command_mark_thread_unread(
    thread_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await mark_thread_unread(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor,
    )
    return result.to_dict()
