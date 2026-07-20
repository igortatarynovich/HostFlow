"""Per-thread message endpoints (list/create) and attachment uploads.

Endpoints:

* GET    /communications/threads/{thread_id}/messages
* POST   /communications/threads/{thread_id}/messages
* POST   /communications/threads/{thread_id}/message-attachments/upload

The list_message_templates endpoint also lives here because templates are
about message composition (lookup by user/target/locale used by reply UI).

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 7/N).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID, uuid4

import sqlalchemy as sa
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import CommunicationMessage
from backend.app.modules.documents.storage import get_uploads_root, sanitize_filename
from backend.app.services.communications_access import assert_comm_feature_access

from .._helpers.access import (
    _ensure_thread_matches_own_company_scope,
    _feature_for_channel,
    _get_tenant_or_404,
    _get_thread_or_404,
    _message_templates_for_user,
    _require_comm_feature,
)
from .._helpers.billing import (
    _load_tenant_license_row,
    _require_outbound_comms_not_billing_blocked,
)
from .._helpers.dto import _message_out
from .._helpers.sla import _touch_thread_from_message
from .._helpers.utils import _now_utc
from ..schemas import (
    MAX_COMM_MESSAGE_ATTACHMENT_BYTES,
    CommunicationMessageAttachmentUploadOut,
    CommunicationMessageCreate,
    CommunicationMessageListResponse,
    CommunicationMessageOut,
    CommunicationMessageTemplateListResponse,
)

router = APIRouter(tags=["communications"])


@router.get("/message-templates", response_model=CommunicationMessageTemplateListResponse)
async def list_message_templates(
    target: str = Query("messages"),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationMessageTemplateListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    normalized_target = str(target or "messages").strip().lower()
    if normalized_target not in {"messages", "email"}:
        normalized_target = "messages"
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=normalized_target)
    tenant = await _get_tenant_or_404(db, tenant_id)
    user_id = str(getattr(current_user, "sub", "") or "").strip() or None
    items = _message_templates_for_user(tenant, user_id=user_id, target=normalized_target)
    return CommunicationMessageTemplateListResponse(items=items, total=len(items))


@router.get("/threads/{thread_id}/messages", response_model=CommunicationMessageListResponse)
async def list_thread_messages(
    thread_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationMessageListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationMessage).where(
        CommunicationMessage.tenant_id == tenant_id,
        CommunicationMessage.thread_id == thread_id,
    )
    stmt = (
        sa.select(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id == thread_id,
        )
        .order_by(sa.asc(CommunicationMessage.created_at))
        .limit(limit)
        .offset(offset)
    )
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationMessageListResponse(items=[_message_out(m) for m in rows], total=total)


@router.post("/threads/{thread_id}/messages", response_model=CommunicationMessageOut, status_code=status.HTTP_201_CREATED)
async def create_thread_message(
    thread_id: str,
    body: CommunicationMessageCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationMessageOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]
    license_row = await _load_tenant_license_row(db, tenant_id)
    if body.direction == "outbound" and not body.is_internal_note:
        _require_outbound_comms_not_billing_blocked(tenant, license_row)
        # C0.1: known origin → durable G13 link required (auto-ensure from thread origin).
        from backend.app.communications.entity_link import (
            ThreadEntityLinkError,
            require_entity_links_for_outbound,
        )

        try:
            await require_entity_links_for_outbound(
                db, tenant_id=tenant_id, thread=thread
            )
        except ThreadEntityLinkError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": getattr(exc, "code", "thread_entity_link_error"),
                    "message": str(getattr(exc, "message", None) or exc),
                    "details": dict(getattr(exc, "details", None) or {}),
                },
            ) from exc
    now = _now_utc()
    msg = CommunicationMessage(
        tenant_id=tenant_id,
        thread_id=thread_id,
        own_company_id=getattr(thread, "own_company_id", None),
        channel=thread.channel,
        message_type=body.message_type,
        direction=body.direction,
        sender_type=body.sender_type or ("user" if body.direction == "outbound" else body.sender_type),
        sender_id=body.sender_id or (str(current_user.sub) if body.direction == "outbound" and getattr(current_user, "sub", None) else None),
        sender_label=body.sender_label,
        sender_address=body.sender_address,
        recipient_type=body.recipient_type,
        recipient_id=body.recipient_id,
        recipient_label=body.recipient_label,
        recipient_address=body.recipient_address,
        subject=body.subject,
        body_text=body.body_text,
        body_html=body.body_html,
        attachments_json=body.attachments_json,
        payload=body.payload,
        external_message_ref=body.external_message_ref,
        delivery_status=body.delivery_status,
        is_internal_note=body.is_internal_note,
        sent_at=body.sent_at if body.sent_at is not None else (now if body.direction == "outbound" and body.delivery_status in {"sent", "delivered", "read"} else None),
        delivered_at=body.delivered_at,
        read_at=body.read_at,
    )
    db.add(msg)
    await db.flush()
    _touch_thread_from_message(thread, msg, tenant=tenant)
    if body.direction == "inbound" and not body.is_internal_note:
        try:
            from backend.app.services import uos_auto_activities

            aid = str(current_user.sub) if getattr(current_user, "sub", None) else ""
            if aid:
                await uos_auto_activities.ensure_inbound_thread_reply_task(db, tenant_id, aid, thread)
        except Exception:
            pass
    await db.commit()
    await db.refresh(msg)
    return _message_out(msg)


@router.post(
    "/threads/{thread_id}/message-attachments/upload",
    response_model=CommunicationMessageAttachmentUploadOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_thread_message_attachment(
    thread_id: str,
    file: UploadFile = File(...),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationMessageAttachmentUploadOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(thread.channel))  # type: ignore[arg-type]

    raw_name = file.filename or "attachment"
    safe = sanitize_filename(raw_name)
    uid = uuid4().hex
    rel_dir_p = Path(tenant_id) / "communications" / thread_id
    stored_name = f"{uid}_{safe}"
    root = get_uploads_root().resolve()
    target_dir = (root / rel_dir_p).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        target_dir.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload path")

    dest = (target_dir / stored_name).resolve()
    try:
        dest.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload path")

    total = 0
    try:
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_COMM_MESSAGE_ATTACHMENT_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={
                            "code": "attachment_too_large",
                            "max_bytes": MAX_COMM_MESSAGE_ATTACHMENT_BYTES,
                        },
                    )
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to store file: {exc}") from exc

    rel_path = dest.relative_to(root).as_posix()
    mime = file.content_type
    return CommunicationMessageAttachmentUploadOut(
        filename=raw_name,
        mime=mime,
        size=total,
        storage_path=rel_path,
    )
