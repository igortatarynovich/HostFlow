"""Communication thread CRUD + lifecycle endpoints.

Endpoints:

* GET    /communications/threads                          — paginated list with filters
* POST   /communications/threads                          — create new thread
* GET    /communications/threads/{thread_id}              — thread detail with messages slice
* PATCH  /communications/threads/{thread_id}              — patch + ops/SLA/escalation merge
* POST   /communications/threads/{thread_id}/read         — mark messages/thread as read
* POST   /communications/threads/reconcile-unread         — recompute unread_count for a batch
* POST   /communications/threads/{thread_id}/assign-auto  — re-run allocator for a thread

Heaviest piece is ``patch_thread`` which merges ``thread_meta`` and
applies SLA/escalation/pause-mode side-effects atomically.

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 7/N).
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.destination_contract import OpaqueResultRef
from backend.app.communications.result_link import (
    ThreadResultLinkError,
    attach_thread_result_from_confirmed_ledger,
    attach_thread_result_link,
    get_thread_result_link,
)
from backend.app.api.v1.utils.own_company import (
    resolve_active_own_company_id,
    resolve_active_own_company_id_optional,
)
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.user import User
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.communications_allocator import allocate_thread

from .._helpers.access import (
    _ensure_thread_matches_own_company_scope,
    _feature_for_channel,
    _get_tenant_or_404,
    _get_thread_or_404,
    _require_any_comm_feature,
    _require_comm_feature,
)
from .._helpers.dto import _message_out, _thread_out
from .._helpers.escalation import _emit_manual_thread_escalation_bridge
from .._helpers.sla import _resolve_thread_sla_alerts
from .._helpers.tenant_settings import (
    _tenant_comm_allowed_roles,
    _tenant_sla_escalation_targets,
)
from .._helpers.utils import _as_dict, _deep_merge_dict, _now_utc
from ..schemas import (
    CommunicationAutoAssignResponse,
    CommunicationMarkReadRequest,
    CommunicationThreadCreate,
    CommunicationThreadDetailResponse,
    CommunicationThreadListResponse,
    CommunicationThreadOut,
    CommunicationThreadPatch,
    CommunicationThreadRematchItemOut,
    CommunicationThreadRematchRequest,
    CommunicationThreadRematchResponse,
    CommunicationThreadResultLinkAttach,
    CommunicationThreadResultLinkOut,
    CommunicationUnreadReconcileRequest,
    CommunicationUnreadReconcileResponse,
)

router = APIRouter(tags=["communications"])


async def _maybe_attach_result_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    module_owner: str | None,
    result_type: str | None,
    result_id: str | None,
    provenance_ledger_id: str | None,
):
    ledger_id = str(provenance_ledger_id or "").strip() or None
    if ledger_id and not (module_owner and result_type and result_id):
        return await attach_thread_result_from_confirmed_ledger(
            db,
            tenant_id=tenant_id,
            thread_id=thread_id,
            ledger_id=ledger_id,
        )
    owner = str(module_owner or "").strip()
    rtype = str(result_type or "").strip()
    rid = str(result_id or "").strip()
    if not (owner or rtype or rid or ledger_id):
        return None
    if not (owner and rtype and rid):
        raise ThreadResultLinkError(
            "result_module_owner, result_type, and result_id are required together "
            "(or pass provenance_ledger_id alone)",
            details={"reason": "incomplete_opaque_result_ref"},
        )
    return await attach_thread_result_link(
        db,
        tenant_id=tenant_id,
        thread_id=thread_id,
        opaque=OpaqueResultRef(
            module_owner=owner,
            result_type=rtype,
            result_id=rid,
        ),
        ledger_id=ledger_id,
    )


@router.get("/threads", response_model=CommunicationThreadListResponse)
@router.get("/threads/", response_model=CommunicationThreadListResponse, include_in_schema=False)
async def list_threads(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    channel: str | None = Query(None),
    status_filter: List[str] | None = Query(None),
    assignee_id: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    include_archived: bool = Query(False),
    q: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationThreadListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if channel:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(channel))
    else:
        await _require_any_comm_feature(db, tenant_id=tenant_id, current_user=current_user, features=["messages", "email"])

    stmt = sa.select(CommunicationThread).where(CommunicationThread.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationThread).where(CommunicationThread.tenant_id == tenant_id)
    if own_company_id:
        oc = CommunicationThread.own_company_id == str(own_company_id)
        stmt = stmt.where(oc)
        count_stmt = count_stmt.where(oc)

    filters = []
    if channel:
        filters.append(CommunicationThread.channel == channel)
    if status_filter:
        filters.append(CommunicationThread.status.in_([str(s) for s in status_filter]))
    if assignee_id:
        filters.append(CommunicationThread.assignee_id == assignee_id)
    if entity_type:
        filters.append(CommunicationThread.entity_type == entity_type)
    if entity_id:
        filters.append(CommunicationThread.entity_id == entity_id)
    if not include_archived:
        filters.append(CommunicationThread.is_archived.is_(False))
    if q:
        like = f"%{q.strip().lower()}%"
        filters.append(
            sa.or_(
                sa.func.lower(sa.func.coalesce(CommunicationThread.subject, "")).like(like),
                sa.func.lower(sa.func.coalesce(CommunicationThread.last_message_preview, "")).like(like),
                sa.func.lower(sa.cast(sa.func.coalesce(CommunicationThread.channel_thread_ref, ""), sa.String)).like(like),
            )
        )

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    stmt = stmt.order_by(
        sa.desc(sa.func.coalesce(CommunicationThread.last_message_at, CommunicationThread.updated_at)),
        sa.desc(CommunicationThread.updated_at),
    ).limit(limit).offset(offset)

    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationThreadListResponse(items=[_thread_out(r) for r in rows], total=total)


@router.post("/threads", response_model=CommunicationThreadOut, status_code=status.HTTP_201_CREATED)
async def create_thread(
    body: CommunicationThreadCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
) -> CommunicationThreadOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(body.channel))
    thread = CommunicationThread(
        tenant_id=tenant_id,
        own_company_id=str(own_company_id),
        channel=body.channel,
        channel_account_id=body.channel_account_id,
        channel_thread_ref=body.channel_thread_ref,
        subject=body.subject,
        status=body.status,
        direction_hint=body.direction_hint,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        linked_company_id=body.linked_company_id,
        linked_candidate_id=body.linked_candidate_id,
        owner_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        assignee_id=body.assignee_id,
        priority=body.priority,
        participants_json=body.participants_json,
        tags_json=body.tags_json,
        thread_meta=body.thread_meta,
        queue_assigned_by="manual" if body.assignee_id else None,
    )
    db.add(thread)
    if body.auto_assign and not body.assignee_id:
        tenant = await _get_tenant_or_404(db, tenant_id)
        await allocate_thread(
            db,
            tenant=tenant,
            thread=thread,
            actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        )
    await db.flush()
    result_link_view = None
    try:
        result_link_view = await _maybe_attach_result_link(
            db,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            module_owner=body.result_module_owner,
            result_type=body.result_type,
            result_id=body.result_id,
            provenance_ledger_id=body.provenance_ledger_id,
        )
    except ThreadResultLinkError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": getattr(exc, "code", "communication_thread_result_link_error"),
                "message": str(getattr(exc, "message", None) or exc),
                "details": dict(getattr(exc, "details", None) or {}),
            },
        ) from exc
    await db.commit()
    await db.refresh(thread)
    return _thread_out(thread, result_link=result_link_view)


@router.get("/threads/{thread_id}", response_model=CommunicationThreadDetailResponse)
async def get_thread(
    thread_id: str,
    messages_limit: int = Query(50, ge=1, le=500),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationThreadDetailResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    messages_stmt = (
        sa.select(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id == thread_id,
        )
        .order_by(sa.asc(CommunicationMessage.created_at))
        .limit(messages_limit)
    )
    msgs = (await db.execute(messages_stmt)).scalars().all()
    result_link = await get_thread_result_link(db, tenant_id=tenant_id, thread_id=thread_id)
    return CommunicationThreadDetailResponse(
        thread=_thread_out(thread, result_link=result_link),
        messages=[_message_out(m) for m in msgs],
    )


@router.post(
    "/threads/{thread_id}/result-link",
    response_model=CommunicationThreadResultLinkOut,
    status_code=status.HTTP_201_CREATED,
)
async def attach_thread_result_link_endpoint(
    thread_id: str,
    body: CommunicationThreadResultLinkAttach,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationThreadResultLinkOut:
    """C1: bind Thread to opaque result ref / confirmed Flights ledger."""
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
    try:
        view = await _maybe_attach_result_link(
            db,
            tenant_id=tenant_id,
            thread_id=thread_id,
            module_owner=body.module_owner,
            result_type=body.result_type,
            result_id=body.result_id,
            provenance_ledger_id=body.provenance_ledger_id,
        )
    except ThreadResultLinkError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": getattr(exc, "code", "communication_thread_result_link_error"),
                "message": str(getattr(exc, "message", None) or exc),
                "details": dict(getattr(exc, "details", None) or {}),
            },
        ) from exc
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "communication_thread_result_link_error",
                "message": "opaque result ref or provenance_ledger_id is required",
                "details": {"reason": "missing_result_link_payload"},
            },
        )
    await db.commit()
    from .._helpers.dto import _result_link_out

    out = _result_link_out(view)
    assert out is not None
    return out


@router.patch("/threads/{thread_id}", response_model=CommunicationThreadOut)
async def patch_thread(
    thread_id: str,
    body: CommunicationThreadPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationThreadOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    patch = body.model_dump(exclude_unset=True)
    meta_patch = patch.pop("thread_meta", None)
    for key, value in patch.items():
        setattr(thread, key, value)
    if meta_patch is not None:
        meta_before_merge = _as_dict(thread.thread_meta)
        merged_meta = _deep_merge_dict(meta_before_merge, _as_dict(meta_patch))
        merged_sla_policy = _as_dict(merged_meta.get("sla_policy"))
        merged_ops = _as_dict(merged_meta.get("ops"))
        now = _now_utc()
        muted = bool(merged_sla_policy.get("muted") or merged_meta.get("sla_muted"))
        merged_sla_policy["muted"] = muted
        merged_meta["sla_muted"] = muted
        if muted and not merged_sla_policy.get("muted_at"):
            merged_sla_policy["muted_at"] = now.isoformat()
        if not muted:
            merged_sla_policy.pop("muted_at", None)
        no_reply_needed = bool(merged_sla_policy.get("no_reply_needed") or merged_meta.get("no_reply_needed"))
        merged_sla_policy["no_reply_needed"] = no_reply_needed
        merged_meta["no_reply_needed"] = no_reply_needed
        if muted:
            await _resolve_thread_sla_alerts(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                close_mode="cancelled",
            )
        if no_reply_needed:
            thread.sla_due_at = None
            if not merged_sla_policy.get("no_reply_needed_at"):
                merged_sla_policy["no_reply_needed_at"] = now.isoformat()
            merged_sla_policy.pop("snoozed_until", None)
            await _resolve_thread_sla_alerts(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                close_mode="cancelled",
            )
        else:
            merged_sla_policy.pop("no_reply_needed_at", None)
            snoozed_until_raw = str(merged_sla_policy.get("snoozed_until") or "").strip()
            if snoozed_until_raw:
                snoozed_until = None
                try:
                    snoozed_until = datetime.fromisoformat(snoozed_until_raw.replace("Z", "+00:00"))
                except Exception:
                    snoozed_until = None
                if snoozed_until is not None and snoozed_until.tzinfo is None:
                    snoozed_until = snoozed_until.replace(tzinfo=timezone.utc)
                if snoozed_until is not None and snoozed_until > now:
                    thread.sla_due_at = snoozed_until
                    merged_sla_policy["snoozed_until"] = snoozed_until.isoformat()
                    await _resolve_thread_sla_alerts(
                        db,
                        tenant_id=tenant_id,
                        thread_id=str(thread.id),
                        close_mode="cancelled",
                    )
                else:
                    merged_sla_policy.pop("snoozed_until", None)

        ops_mode = str(merged_ops.get("mode") or "").strip().lower()
        if ops_mode == "escalated":
            escalation = _as_dict(merged_ops.get("escalation"))
            prev_esc = _as_dict(_as_dict(meta_before_merge.get("ops")).get("escalation"))
            prev_target = _as_dict(prev_esc.get("target"))
            target = _as_dict(escalation.get("target"))
            reason = str(escalation.get("reason") or "").strip()
            has_target = any(
                str(target.get(k) or "").strip()
                for k in ("queue", "role", "user_id")
            )
            prev_reason = str(prev_esc.get("reason") or "").strip()
            has_prev_target = any(
                str(prev_target.get(k) or "").strip()
                for k in ("queue", "role", "user_id")
            )
            if (not reason and prev_reason) or (not has_target and has_prev_target):
                escalation = {**prev_esc, **escalation}
                escalation["target"] = {**prev_target, **_as_dict(escalation.get("target"))}
                merged_ops["escalation"] = escalation
                reason = str(escalation.get("reason") or "").strip()
                target = _as_dict(escalation.get("target"))
                has_target = any(
                    str(target.get(k) or "").strip()
                    for k in ("queue", "role", "user_id")
                )
            if not reason:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "ops_escalation_reason_required",
                        "message": "Escalation reason is required for escalated mode",
                    },
                )
            if not has_target:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "ops_escalation_target_required",
                        "message": "Escalation target is required for escalated mode",
                    },
                )
            queue_target = str(target.get("queue") or "").strip()
            if queue_target:
                allowed_targets = _tenant_sla_escalation_targets(tenant)
                if allowed_targets and queue_target not in allowed_targets:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_unknown_queue",
                            "message": "Escalation queue target is not allowed by tenant SLA settings",
                            "allowed_targets": sorted(allowed_targets),
                        },
                    )
            role_target = str(target.get("role") or "").strip().lower()
            if role_target:
                if not re.match(r"^[a-z][a-z0-9_-]{1,63}$", role_target):
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_invalid_role",
                            "message": "Escalation role target has invalid format",
                            "role": role_target,
                        },
                    )
                allowed_roles = _tenant_comm_allowed_roles(tenant)
                if allowed_roles and role_target not in allowed_roles:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_unknown_role",
                            "message": "Escalation role target is not allowed by tenant communications access settings",
                            "allowed_roles": sorted(allowed_roles),
                        },
                    )
                target["role"] = role_target
            user_target = str(target.get("user_id") or "").strip()
            if user_target:
                try:
                    UUID(user_target)
                except Exception:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_invalid_user_id",
                            "message": "Escalation user target must be a valid UUID",
                            "user_id": user_target,
                        },
                    )
                user_row = (
                    await db.execute(
                        sa.select(User.id)
                        .where(
                            User.id == user_target,
                            User.tenant_id == tenant_id,
                            User.is_active.is_(True),
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if user_row is None:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "ops_escalation_target_unknown_user",
                            "message": "Escalation user target does not belong to current tenant or is inactive",
                            "user_id": user_target,
                        },
                    )
            escalation["reason"] = reason
            escalation["target"] = target
            escalation["escalated_at"] = str(escalation.get("escalated_at") or now.isoformat())
            merged_ops["escalation"] = escalation
            prev_ops_before = _as_dict(meta_before_merge.get("ops"))
            prev_mode_before = str(prev_ops_before.get("mode") or "").strip().lower()
            if prev_mode_before != "escalated":
                await _emit_manual_thread_escalation_bridge(
                    db,
                    tenant_id=tenant_id,
                    thread=thread,
                    escalation=dict(escalation),
                    actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
                )
            if str(thread.priority or "").strip().lower() != "high":
                thread.priority = "high"

        if ops_mode in ("later", "paused"):
            paused_until_raw = str(merged_ops.get("paused_until") or "").strip()
            paused_until = None
            if paused_until_raw:
                try:
                    paused_until = datetime.fromisoformat(paused_until_raw.replace("Z", "+00:00"))
                except Exception:
                    paused_until = None
            if paused_until is not None and paused_until.tzinfo is None:
                paused_until = paused_until.replace(tzinfo=timezone.utc)
            if paused_until is not None and paused_until > now:
                merged_ops["mode"] = "later"
                merged_ops["paused_until"] = paused_until.isoformat()
                merged_sla_policy["no_reply_needed"] = False
                merged_meta["no_reply_needed"] = False
                merged_sla_policy["snoozed_until"] = paused_until.isoformat()
                thread.sla_due_at = paused_until
                await _resolve_thread_sla_alerts(
                    db,
                    tenant_id=tenant_id,
                    thread_id=str(thread.id),
                    close_mode="cancelled",
                )
            else:
                merged_ops["mode"] = "in_work"
                merged_ops.pop("paused_until", None)
                merged_sla_policy.pop("snoozed_until", None)
        else:
            merged_ops.pop("paused_until", None)

        merged_meta["ops"] = merged_ops
        merged_meta["sla_policy"] = merged_sla_policy
        thread.thread_meta = merged_meta
    thread.updated_at = _now_utc()
    await db.commit()
    await db.refresh(thread)
    return _thread_out(thread)


@router.post("/threads/{thread_id}/read", response_model=CommunicationThreadOut)
async def mark_thread_read(
    thread_id: str,
    body: CommunicationMarkReadRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationThreadOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    now = _now_utc()
    stmt = sa.update(CommunicationMessage).where(
        CommunicationMessage.tenant_id == tenant_id,
        CommunicationMessage.thread_id == thread_id,
        CommunicationMessage.direction == "inbound",
        CommunicationMessage.read_at.is_(None),
    )
    if body.message_ids:
        stmt = stmt.where(CommunicationMessage.id.in_([str(x) for x in body.message_ids]))
    stmt = stmt.values(read_at=now, delivery_status=sa.case((CommunicationMessage.delivery_status == "delivered", "read"), else_=CommunicationMessage.delivery_status))
    await db.execute(stmt)
    if body.mark_thread:
        thread.unread_count = 0
        thread.updated_at = now
    await db.commit()
    await db.refresh(thread)
    return _thread_out(thread)



@router.post("/threads/rematch-unlinked", response_model=CommunicationThreadRematchResponse)
async def rematch_unlinked_threads(
    body: CommunicationThreadRematchRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationThreadRematchResponse:
    """G15 rematch stub — full inbound-matching service not on this release line."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(
        db, tenant_id=tenant_id, current_user=current_user, feature="email"
    )
    _ = own_company_id
    ids = [str(x).strip() for x in (body.thread_ids or []) if str(x).strip()]
    items = [
        CommunicationThreadRematchItemOut(
            thread_id=tid,
            confidence="none",
            auto_linked=False,
            skipped=True,
            skip_reason="rematch_service_unavailable",
        )
        for tid in ids[: max(1, min(int(body.limit or 100), 500))]
    ]
    return CommunicationThreadRematchResponse(
        processed=len(items),
        linked=0,
        ambiguous=0,
        none=0,
        skipped=len(items),
        dry_run=bool(body.dry_run),
        items=items,
        unavailable_reason="inbound_matching_service_not_deployed",
    )


@router.post("/threads/reconcile-unread", response_model=CommunicationUnreadReconcileResponse)
async def reconcile_thread_unread(
    body: CommunicationUnreadReconcileRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationUnreadReconcileResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if body.channel:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(body.channel))
    else:
        await _require_any_comm_feature(db, tenant_id=tenant_id, current_user=current_user, features=["messages", "email"])

    threads_stmt = sa.select(CommunicationThread.id, CommunicationThread.unread_count).where(
        CommunicationThread.tenant_id == tenant_id
    )
    if own_company_id:
        threads_stmt = threads_stmt.where(CommunicationThread.own_company_id == str(own_company_id))
    if body.channel:
        threads_stmt = threads_stmt.where(CommunicationThread.channel == body.channel)
    if not body.include_archived:
        threads_stmt = threads_stmt.where(CommunicationThread.is_archived.is_(False))
    threads_stmt = threads_stmt.order_by(
        sa.desc(sa.func.coalesce(CommunicationThread.last_message_at, CommunicationThread.updated_at)),
        sa.desc(CommunicationThread.updated_at),
    ).limit(body.limit)
    thread_rows = (await db.execute(threads_stmt)).all()
    if not thread_rows:
        return CommunicationUnreadReconcileResponse(processed=0, updated=0, total_unread=0)

    thread_ids = [str(row[0]) for row in thread_rows]
    counts_stmt = (
        sa.select(CommunicationMessage.thread_id, sa.func.count())
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id.in_(thread_ids),
            CommunicationMessage.direction == "inbound",
            CommunicationMessage.read_at.is_(None),
            sa.not_(
                sa.or_(
                    sa.func.coalesce(
                        CommunicationMessage.payload.op("->>")("telegram_command"),
                        "",
                    )
                    == "true",
                    sa.and_(
                        CommunicationMessage.channel == "telegram",
                        CommunicationMessage.body_text.is_not(None),
                        CommunicationMessage.body_text.like("/%"),
                    ),
                )
            ),
        )
        .group_by(CommunicationMessage.thread_id)
    )
    unread_map = {str(thread_id): int(count or 0) for thread_id, count in (await db.execute(counts_stmt)).all()}

    now = _now_utc()
    updated = 0
    total_unread = 0
    for thread_id, current_unread in thread_rows:
        thread_id_str = str(thread_id)
        expected = int(unread_map.get(thread_id_str, 0))
        total_unread += expected
        current = int(current_unread or 0)
        if current == expected:
            continue
        await db.execute(
            sa.update(CommunicationThread)
            .where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.id == thread_id_str,
            )
            .values(unread_count=expected, updated_at=now)
        )
        updated += 1

    if updated > 0:
        await db.commit()
    return CommunicationUnreadReconcileResponse(processed=len(thread_rows), updated=updated, total_unread=total_unread)


@router.post("/threads/{thread_id}/assign-auto", response_model=CommunicationAutoAssignResponse)
async def auto_assign_thread(
    thread_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationAutoAssignResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    result = await allocate_thread(
        db,
        tenant=tenant,
        thread=thread,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )
    await db.commit()
    await db.refresh(thread)
    return CommunicationAutoAssignResponse(
        assigned=bool(result.get("assigned")),
        thread=_thread_out(thread),
        reason=result.get("reason"),
        strategy=result.get("strategy"),
        assignee_id=result.get("assignee_id"),
        candidates=result.get("candidates") or [],
    )
