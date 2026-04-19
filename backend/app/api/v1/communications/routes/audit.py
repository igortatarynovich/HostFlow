"""Allocator + commands audit endpoints for the communications API.

Endpoints:
    POST /communications/allocator/preview
    GET  /communications/allocator/audit
    POST /communications/commands/audit/batch
    GET  /communications/commands/audit
"""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import (
    CommunicationAllocationAudit,
    CommunicationCommandAudit,
    CommunicationThread,
)
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.communications_allocator import preview_allocation

from .._helpers.access import (
    _feature_for_channel,
    _get_tenant_or_404,
    _require_comm_feature,
)
from .._helpers.dto import _allocation_audit_out, _command_audit_out
from .._helpers.utils import _as_dict, _now_utc
from ..schemas import (
    CommunicationAllocationAuditListResponse,
    CommunicationAllocatorPreviewRequest,
    CommunicationAllocatorPreviewResponse,
    CommunicationCommandAuditBatchCreate,
    CommunicationCommandAuditBatchResponse,
    CommunicationCommandAuditListResponse,
)

router = APIRouter(tags=["communications"])


@router.post("/allocator/preview", response_model=CommunicationAllocatorPreviewResponse)
async def allocator_preview(
    body: CommunicationAllocatorPreviewRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAllocatorPreviewResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="communicationsAdmin")
    result = await preview_allocation(
        db,
        tenant=tenant,
        channel=body.channel,
        now_override=body.at,
    )
    return CommunicationAllocatorPreviewResponse(
        assigned=bool(result.get("assigned")),
        reason=result.get("reason"),
        strategy=result.get("strategy"),
        assignee_id=result.get("winner_manager_id"),
        evaluated_at=result.get("evaluated_at"),
        candidates=result.get("candidates") or [],
    )


@router.get("/allocator/audit", response_model=CommunicationAllocationAuditListResponse)
async def list_allocator_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    mode: str | None = Query(None),
    channel: str | None = Query(None),
    thread_id: str | None = Query(None),
    assignee_id: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAllocationAuditListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    stmt = sa.select(CommunicationAllocationAudit).where(CommunicationAllocationAudit.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationAllocationAudit).where(CommunicationAllocationAudit.tenant_id == tenant_id)
    filters = []
    if mode:
        filters.append(CommunicationAllocationAudit.mode == mode)
    if channel:
        filters.append(CommunicationAllocationAudit.channel == channel)
    if thread_id:
        filters.append(CommunicationAllocationAudit.thread_id == thread_id)
    if assignee_id:
        filters.append(CommunicationAllocationAudit.assignee_id == assignee_id)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.desc(sa.func.coalesce(CommunicationAllocationAudit.evaluated_at, CommunicationAllocationAudit.created_at))).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationAllocationAuditListResponse(items=[_allocation_audit_out(r) for r in rows], total=total)


@router.post("/commands/audit/batch", response_model=CommunicationCommandAuditBatchResponse)
async def create_command_audit_batch(
    body: CommunicationCommandAuditBatchCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationCommandAuditBatchResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(
        tenant=tenant,
        current_user=current_user,
        tenant_id=tenant_id,
        feature=_feature_for_channel(body.channel),
    )  # type: ignore[arg-type]

    requested_ids = [str(x).strip() for x in (body.thread_ids or []) if str(x).strip()]
    unique_ids: list[str] = []
    seen: set[str] = set()
    for tid in requested_ids:
        if tid in seen:
            continue
        seen.add(tid)
        unique_ids.append(tid)
    if not unique_ids:
        return CommunicationCommandAuditBatchResponse(created=0, items=[])

    thread_rows = (
        await db.execute(
            sa.select(CommunicationThread.id, CommunicationThread.channel).where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.id.in_(unique_ids),
            )
        )
    ).all()
    allowed_thread_ids = [str(r[0]) for r in thread_rows if str(r[1] or "").strip().lower() == str(body.channel or "").strip().lower()]
    if not allowed_thread_ids:
        return CommunicationCommandAuditBatchResponse(created=0, items=[])

    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    executed_at = body.executed_at or _now_utc()
    action_count = len([a for a in (body.actions_json or []) if isinstance(a, dict)])
    created_rows: list[CommunicationCommandAudit] = []
    for thread_id in allowed_thread_ids:
        row = CommunicationCommandAudit(
            tenant_id=tenant_id,
            thread_id=thread_id,
            channel=str(body.channel or "").strip().lower(),
            command_id=body.command_id,
            command_label=body.command_label,
            actor_user_id=actor_id,
            action_count=action_count,
            actions_json=[a for a in (body.actions_json or []) if isinstance(a, dict)],
            payload=_as_dict(body.payload),
            executed_at=executed_at,
        )
        db.add(row)
        created_rows.append(row)
    await db.commit()
    for row in created_rows:
        await db.refresh(row)
    return CommunicationCommandAuditBatchResponse(created=len(created_rows), items=[_command_audit_out(r) for r in created_rows])


@router.get("/commands/audit", response_model=CommunicationCommandAuditListResponse)
async def list_command_audit(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    channel: str | None = Query(None),
    thread_id: str | None = Query(None),
    command_id: str | None = Query(None),
    actor_user_id: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationCommandAuditListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    stmt = sa.select(CommunicationCommandAudit).where(CommunicationCommandAudit.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationCommandAudit).where(CommunicationCommandAudit.tenant_id == tenant_id)
    filters = []
    if channel:
        filters.append(CommunicationCommandAudit.channel == str(channel).strip().lower())
    if thread_id:
        filters.append(CommunicationCommandAudit.thread_id == thread_id)
    if command_id:
        filters.append(CommunicationCommandAudit.command_id == command_id)
    if actor_user_id:
        filters.append(CommunicationCommandAudit.actor_user_id == actor_user_id)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.desc(sa.func.coalesce(CommunicationCommandAudit.executed_at, CommunicationCommandAudit.created_at))).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationCommandAuditListResponse(items=[_command_audit_out(r) for r in rows], total=total)
