"""C1.2 — Workspace Command HTTP surface.

POST /communications/threads/{thread_id}/commands/{command}

Every success returns ThreadContext (not bare ThreadOut).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.communications.workspace_commands import (
    WorkspaceCommandError,
    _UNSET,
    assign_thread,
    cancel_next_action,
    close_thread,
    complete_next_action,
    delete_thread,
    expect_work_version,
    mark_thread_read,
    mark_thread_unread,
    pause_sla,
    reopen_thread,
    restore_thread,
    resume_sla,
    set_next_action,
    set_thread_links,
    set_thread_priority,
    set_thread_tags,
    unassign_thread,
    update_thread_workflow,
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


class ConcurrencyBody(BaseModel):
    expected_work_version: int | None = None


class AssignThreadBody(ConcurrencyBody):
    assignee_id: str = Field(..., min_length=1, max_length=36)
    reason: str = Field(default="manual", max_length=64)


class UnassignThreadBody(ConcurrencyBody):
    reason: str = Field(default="manual", max_length=64)


class SetNextActionBody(ConcurrencyBody):
    action_type: str = Field(..., min_length=1, max_length=64)
    owner_id: str | None = Field(default=None, max_length=36)
    due_at: datetime | None = None
    source: str = Field(default="manual", max_length=32)
    note: str | None = Field(default=None, max_length=2000)


class NextActionTargetBody(ConcurrencyBody):
    next_action_id: str | None = Field(default=None, max_length=36)


class ResumeSlaBody(ConcurrencyBody):
    target_due_at: datetime | None = None


class SetThreadPriorityBody(ConcurrencyBody):
    priority: str = Field(..., min_length=1, max_length=16)


class SetThreadTagsBody(ConcurrencyBody):
    tags: list[Any] = Field(default_factory=list)


class UpdateThreadWorkflowBody(ConcurrencyBody):
    thread_meta: dict[str, Any] = Field(default_factory=dict)


class SetThreadLinksBody(ConcurrencyBody):
    linked_candidate_id: str | None = None
    linked_company_id: str | None = None
    thread_meta: dict[str, Any] | None = None


def _http_command_error(exc: WorkspaceCommandError) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT
        if exc.code == "stale_work_version"
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(
        status_code=code,
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
    return db, tenant_id, tenant, thread, actor


async def _run(expected: int | None, coro):
    try:
        with expect_work_version(expected):
            return await coro
    except WorkspaceCommandError as exc:
        raise _http_command_error(exc) from exc


@router.post("/threads/{thread_id}/commands/AssignThread")
async def command_assign_thread(
    thread_id: str,
    body: AssignThreadBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version,
        assign_thread(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            assignee_id=body.assignee_id,
            reason=body.reason,
            command_id="AssignThread",
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/ReassignThread")
async def command_reassign_thread(
    thread_id: str,
    body: AssignThreadBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version,
        assign_thread(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            assignee_id=body.assignee_id,
            reason=body.reason,
            command_id="ReassignThread",
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/UnassignThread")
async def command_unassign_thread(
    thread_id: str,
    body: UnassignThreadBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        unassign_thread(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            reason=(body.reason if body else "manual"),
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/MarkThreadRead")
async def command_mark_thread_read(
    thread_id: str,
    body: ConcurrencyBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        mark_thread_read(
            db, tenant_id=tenant_id, thread=thread, actor_user_id=actor
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/MarkThreadUnread")
async def command_mark_thread_unread(
    thread_id: str,
    body: ConcurrencyBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        mark_thread_unread(
            db, tenant_id=tenant_id, thread=thread, actor_user_id=actor
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/SetNextAction")
async def command_set_next_action(
    thread_id: str,
    body: SetNextActionBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version,
        set_next_action(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            action_type=body.action_type,
            owner_id=body.owner_id,
            due_at=body.due_at,
            source=body.source,
            note=body.note,
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/CompleteNextAction")
async def command_complete_next_action(
    thread_id: str,
    body: NextActionTargetBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        complete_next_action(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            next_action_id=body.next_action_id if body else None,
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/CancelNextAction")
async def command_cancel_next_action(
    thread_id: str,
    body: NextActionTargetBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        cancel_next_action(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            next_action_id=body.next_action_id if body else None,
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/PauseSLA")
async def command_pause_sla(
    thread_id: str,
    body: ConcurrencyBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        pause_sla(db, tenant_id=tenant_id, thread=thread, actor_user_id=actor),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/ResumeSLA")
async def command_resume_sla(
    thread_id: str,
    body: ResumeSlaBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        resume_sla(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            target_due_at=body.target_due_at if body else None,
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/CloseThread")
async def command_close_thread(
    thread_id: str,
    body: ConcurrencyBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        close_thread(db, tenant_id=tenant_id, thread=thread, actor_user_id=actor),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/ReopenThread")
async def command_reopen_thread(
    thread_id: str,
    body: ConcurrencyBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        reopen_thread(db, tenant_id=tenant_id, thread=thread, actor_user_id=actor),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/SetThreadPriority")
async def command_set_thread_priority(
    thread_id: str,
    body: SetThreadPriorityBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version,
        set_thread_priority(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            priority=body.priority,
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/SetThreadTags")
async def command_set_thread_tags(
    thread_id: str,
    body: SetThreadTagsBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version,
        set_thread_tags(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            tags=body.tags,
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/DeleteThread")
async def command_delete_thread(
    thread_id: str,
    body: ConcurrencyBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        delete_thread(db, tenant_id=tenant_id, thread=thread, actor_user_id=actor),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/RestoreThread")
async def command_restore_thread(
    thread_id: str,
    body: ConcurrencyBody | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version if body else None,
        restore_thread(db, tenant_id=tenant_id, thread=thread, actor_user_id=actor),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/UpdateThreadWorkflow")
async def command_update_thread_workflow(
    thread_id: str,
    body: UpdateThreadWorkflowBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    result = await _run(
        body.expected_work_version,
        update_thread_workflow(
            db,
            tenant_id=tenant_id,
            tenant=tenant,
            thread=thread,
            actor_user_id=actor,
            thread_meta=body.thread_meta,
        ),
    )
    return result.to_dict()


@router.post("/threads/{thread_id}/commands/SetThreadLinks")
async def command_set_thread_links(
    thread_id: str,
    body: SetThreadLinksBody,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> dict:
    db, tenant_id, _tenant, thread, actor = await _load_thread_for_command(
        thread_id=thread_id,
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )
    fields_set = body.model_fields_set
    result = await _run(
        body.expected_work_version,
        set_thread_links(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor,
            linked_candidate_id=(
                body.linked_candidate_id if "linked_candidate_id" in fields_set else _UNSET
            ),
            linked_company_id=(
                body.linked_company_id if "linked_company_id" in fields_set else _UNSET
            ),
            thread_meta=body.thread_meta,
        ),
    )
    return result.to_dict()
