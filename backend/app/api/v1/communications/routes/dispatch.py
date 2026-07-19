"""Dispatch / scheduler / email-worker routes for the communications API.

Includes:

* ``POST /messages/{message_id}/dispatch`` — single-message send;
* ``POST /dispatch/queued`` — batch processing of queued outbound messages
  (with per-channel adapter selection, retry-bookkeeping, SLA cleanup);
* ``PATCH /messages/{message_id}/delivery-status`` — provider-callback
  delivery-status sink (sent → delivered → read);
* ``GET /scheduler/status`` and ``POST /scheduler/run-now`` — admin
  controls for the in-process scheduler;
* ``POST /email/worker/dispatch`` — email-only convenience wrapper around
  ``/dispatch/queued`` (used by ``services.communications_scheduler``).

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 4/N). Mounts under the same
``/communications`` prefix carried by the parent router.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.send_pipeline import (
    CommunicationSendRequest,
    authorize_outbound_communication,
    template_metadata_from_mapping,
)
from backend.app.api.v1.utils.own_company import (
    resolve_active_own_company_id_optional,
)
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import (
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.services import billing_restrictions
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.communications_scheduler import (
    run_scheduler_tick_once,
    scheduler_runtime_status,
)

from .._helpers.access import (
    _ensure_thread_matches_own_company_scope,
    _feature_for_channel,
    _get_thread_or_404,
    _get_tenant_or_404,
    _require_any_comm_feature,
    _require_comm_feature,
)
from .._helpers.billing import (
    _load_tenant_license_row,
    _require_outbound_comms_not_billing_blocked,
)
from .._helpers.dispatch import (
    _dispatch_attempt_count,
    _dispatch_email_message_via_tenant_smtp,
    _dispatch_instagram_message_via_graph_api,
    _dispatch_messenger_message_via_graph_api,
    _dispatch_next_retry_at,
    _dispatch_telegram_message_via_bot_api,
    _dispatch_viber_message_via_bot_api,
    _dispatch_whatsapp_message_via_cloud_api,
    _maybe_defer_outbound_for_working_hours,
    _mock_dispatch_outbound_message,
    _schedule_dispatch_retry,
)
from .._helpers.dto import _message_out, _thread_out
from .._helpers.sla import _resolve_thread_sla_alerts, _touch_thread_from_message
from .._helpers.utils import _as_dict, _now_utc
from ..schemas import (
    CommunicationDeliveryStatusPatch,
    CommunicationDispatchQueuedRequest,
    CommunicationDispatchQueuedResponse,
    CommunicationDispatchRequest,
    CommunicationDispatchResponse,
    CommunicationEmailWorkerDispatchRequest,
    CommunicationMessageOut,
    CommunicationSchedulerRunNowResponse,
    CommunicationSchedulerStatusOut,
)

__all__ = [
    "router",
    "dispatch_message",
    "dispatch_queued_messages",
    "patch_message_delivery_status",
    "get_communications_scheduler_status",
    "run_communications_scheduler_now",
    "run_email_dispatch_worker",
]


router = APIRouter(tags=["communications"])


def _payload_dict(msg: CommunicationMessage) -> dict:
    raw = getattr(msg, "payload", None)
    return dict(raw) if isinstance(raw, dict) else {}


async def _authorize_outbound_or_reason(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    body: CommunicationDispatchRequest,
) -> str | None:
    """C5: outbound non-notes must pass the Communication Pipeline. Returns deny reason or None."""
    if bool(getattr(msg, "is_internal_note", False)):
        return None
    if str(getattr(msg, "direction", "") or "") != "outbound":
        return None
    if body.simulate_failure:
        # Still require authorization before simulated failure (no domain guess).
        pass

    payload = _payload_dict(msg)
    purpose = (
        str(body.communication_purpose or "").strip()
        or str(payload.get("communication_purpose") or "").strip()
    )
    template_raw = body.template_metadata
    if not isinstance(template_raw, dict):
        template_raw = payload.get("template_metadata_v1")
    template = template_metadata_from_mapping(
        template_raw if isinstance(template_raw, dict) else None
    )
    locale = str(body.locale or payload.get("locale") or "").strip() or None

    if not purpose or template is None:
        return "communication_pipeline_required"

    auth = await authorize_outbound_communication(
        db,
        CommunicationSendRequest(
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            channel=str(thread.channel or msg.channel or ""),
            communication_purpose=purpose,
            template=template,
            locale=locale,
        ),
    )
    if not auth.allowed:
        return str(auth.reason_code or "communication_pipeline_denied")
    return None


@router.post(
    "/messages/{message_id}/dispatch",
    response_model=CommunicationDispatchResponse,
)
async def dispatch_message(
    message_id: str,
    body: CommunicationDispatchRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationDispatchResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    msg = await db.get(CommunicationMessage, message_id)
    if msg is None or str(msg.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Message not found")
    thread = await _get_thread_or_404(db, tenant_id, str(msg.thread_id))
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(
        tenant=tenant,
        current_user=current_user,
        tenant_id=tenant_id,
        feature=_feature_for_channel(thread.channel),  # type: ignore[arg-type]
    )
    license_row = await _load_tenant_license_row(db, tenant_id)
    if (
        str(getattr(msg, "direction", "") or "") == "outbound"
        and not bool(getattr(msg, "is_internal_note", False))
        and not body.simulate_failure
    ):
        _require_outbound_comms_not_billing_blocked(tenant, license_row)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None

    pipeline_reason = await _authorize_outbound_or_reason(
        db, tenant_id=tenant_id, thread=thread, msg=msg, body=body
    )
    if pipeline_reason is not None:
        msg.delivery_status = "failed"
        msg.error_message = pipeline_reason[:500]
        thread.updated_at = _now_utc()
        await db.commit()
        await db.refresh(msg)
        await db.refresh(thread)
        return CommunicationDispatchResponse(
            dispatched=False,
            message=_message_out(msg),
            thread=_thread_out(thread),
            reason=pipeline_reason,
        )

    if thread.channel == "email" and not body.simulate_failure:
        reason = await _dispatch_email_message_via_tenant_smtp(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "telegram" and not body.simulate_failure:
        reason = await _dispatch_telegram_message_via_bot_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "whatsapp" and not body.simulate_failure:
        reason = await _dispatch_whatsapp_message_via_cloud_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "messenger" and not body.simulate_failure:
        reason = await _dispatch_messenger_message_via_graph_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "instagram" and not body.simulate_failure:
        reason = await _dispatch_instagram_message_via_graph_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    elif thread.channel == "viber" and not body.simulate_failure:
        reason = await _dispatch_viber_message_via_bot_api(
            db,
            tenant_id=tenant_id,
            thread=thread,
            msg=msg,
            actor_id=actor_id,
        )
        if reason is None and body.mark_delivered:
            msg.delivery_status = "delivered"
            msg.delivered_at = msg.delivered_at or _now_utc()
    else:
        reason = _mock_dispatch_outbound_message(
            thread=thread,
            msg=msg,
            actor_id=actor_id,
            mark_delivered=bool(body.mark_delivered),
            simulate_failure=bool(body.simulate_failure),
            provider_message_ref=body.provider_message_ref,
            provider_payload=body.provider_payload,
        )
    if reason is None:
        _touch_thread_from_message(thread, msg)
        await _resolve_thread_sla_alerts(
            db,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            close_mode="done",
        )
    thread.updated_at = _now_utc()
    await db.commit()
    await db.refresh(msg)
    await db.refresh(thread)
    return CommunicationDispatchResponse(
        dispatched=reason is None,
        message=_message_out(msg),
        thread=_thread_out(thread),
        reason=reason,
    )


@router.post(
    "/dispatch/queued",
    response_model=CommunicationDispatchQueuedResponse,
)
async def dispatch_queued_messages(
    body: CommunicationDispatchQueuedRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> CommunicationDispatchQueuedResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if body.channel:
        await _require_comm_feature(
            db,
            tenant_id=tenant_id,
            current_user=current_user,
            feature=_feature_for_channel(body.channel),
        )
    elif body.only_email:
        await _require_comm_feature(
            db, tenant_id=tenant_id, current_user=current_user, feature="email"
        )
    else:
        await _require_any_comm_feature(
            db,
            tenant_id=tenant_id,
            current_user=current_user,
            features=["messages", "email"],
        )
    tenant = await _get_tenant_or_404(db, tenant_id)
    license_row = await _load_tenant_license_row(db, tenant_id)
    if (
        billing_restrictions.tenant_billing_blocks_outbound_comms(tenant, license_row)
        and not body.simulate_failure
    ):
        return CommunicationDispatchQueuedResponse(
            processed=0, dispatched=0, failed=0, items=[]
        )
    fetch_limit = max(body.limit, min(body.limit * 4, 800))
    stmt = (
        sa.select(CommunicationMessage)
        .join(
            CommunicationThread,
            CommunicationThread.id == CommunicationMessage.thread_id,
        )
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.direction == "outbound",
            CommunicationMessage.delivery_status == "queued",
            CommunicationMessage.is_internal_note.is_(False),
        )
        .order_by(sa.asc(CommunicationMessage.created_at))
        .limit(fetch_limit)
    )
    if own_company_id:
        stmt = stmt.where(CommunicationThread.own_company_id == str(own_company_id))
    if body.channel:
        stmt = stmt.where(CommunicationMessage.channel == body.channel)
    elif body.only_email:
        stmt = stmt.where(CommunicationMessage.channel == "email")
    rows = (await db.execute(stmt)).scalars().all()

    items: List[CommunicationDispatchResponse] = []
    dispatched_count = 0
    failed_count = 0
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None

    thread_cache: Dict[str, CommunicationThread] = {}
    attempted_count = 0
    now_ref = _now_utc()
    for msg in rows:
        if attempted_count >= body.limit:
            break
        next_retry_at = _dispatch_next_retry_at(msg)
        if next_retry_at is not None and next_retry_at > now_ref:
            continue
        thread = thread_cache.get(str(msg.thread_id))
        if thread is None:
            thread = await _get_thread_or_404(db, tenant_id, str(msg.thread_id))
            thread_cache[str(thread.id)] = thread
        # G-4.5 outbound working-hours gate. Bypassed on `simulate_failure`
        # (tests don't want to be rescheduled) and when the tenant flag is
        # off (default) — helper returns None in both cases without any
        # model lookup beyond the short-circuit.
        if not body.simulate_failure:
            deferral_target = await _maybe_defer_outbound_for_working_hours(
                db,
                tenant=tenant,
                thread=thread,
                msg=msg,
                now=now_ref,
            )
            if deferral_target is not None:
                items.append(
                    CommunicationDispatchResponse(
                        dispatched=False,
                        message=_message_out(msg),
                        thread=_thread_out(thread),
                        reason="deferred_outside_working_hours",
                    )
                )
                continue
        attempted_count += 1
        attempt_before = _dispatch_attempt_count(msg)
        # C5: queued retries must re-enter the same Communication Pipeline.
        queue_body = CommunicationDispatchRequest(
            mark_delivered=bool(body.mark_delivered),
            simulate_failure=bool(body.simulate_failure),
        )
        pipeline_reason = await _authorize_outbound_or_reason(
            db, tenant_id=tenant_id, thread=thread, msg=msg, body=queue_body
        )
        if pipeline_reason is not None:
            msg.delivery_status = "failed"
            msg.error_message = pipeline_reason[:500]
            failed_count += 1
            items.append(
                CommunicationDispatchResponse(
                    dispatched=False,
                    message=_message_out(msg),
                    thread=_thread_out(thread),
                    reason=pipeline_reason,
                )
            )
            continue
        if thread.channel == "email" and not body.simulate_failure:
            reason = await _dispatch_email_message_via_tenant_smtp(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "telegram" and not body.simulate_failure:
            reason = await _dispatch_telegram_message_via_bot_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "whatsapp" and not body.simulate_failure:
            reason = await _dispatch_whatsapp_message_via_cloud_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "messenger" and not body.simulate_failure:
            reason = await _dispatch_messenger_message_via_graph_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "instagram" and not body.simulate_failure:
            reason = await _dispatch_instagram_message_via_graph_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        elif thread.channel == "viber" and not body.simulate_failure:
            reason = await _dispatch_viber_message_via_bot_api(
                db,
                tenant_id=tenant_id,
                thread=thread,
                msg=msg,
                actor_id=actor_id,
            )
            if reason is None and body.mark_delivered:
                msg.delivery_status = "delivered"
                msg.delivered_at = msg.delivered_at or _now_utc()
        else:
            reason = _mock_dispatch_outbound_message(
                thread=thread,
                msg=msg,
                actor_id=actor_id,
                mark_delivered=bool(body.mark_delivered),
                simulate_failure=bool(body.simulate_failure),
                provider_message_ref=None,
                provider_payload={"batch": True},
            )
        if reason is None:
            dispatched_count += 1
            _touch_thread_from_message(thread, msg)
            await _resolve_thread_sla_alerts(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                close_mode="done",
            )
        else:
            failed_count += 1
            _schedule_dispatch_retry(
                msg=msg,
                reason=reason,
                actor_id=actor_id,
                now=_now_utc(),
                current_attempt=attempt_before,
            )
        thread.updated_at = _now_utc()
        items.append(
            CommunicationDispatchResponse(
                dispatched=reason is None,
                message=_message_out(msg),
                thread=_thread_out(thread),
                reason=reason,
            )
        )

    await db.commit()
    return CommunicationDispatchQueuedResponse(
        processed=attempted_count,
        dispatched=dispatched_count,
        failed=failed_count,
        items=items,
    )


@router.patch(
    "/messages/{message_id}/delivery-status",
    response_model=CommunicationMessageOut,
)
async def patch_message_delivery_status(
    message_id: str,
    body: CommunicationDeliveryStatusPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationMessageOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    msg = await db.get(CommunicationMessage, message_id)
    if msg is None or str(msg.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Message not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(
        tenant=tenant,
        current_user=current_user,
        tenant_id=tenant_id,
        feature=_feature_for_channel(msg.channel),  # type: ignore[arg-type]
    )
    if body.external_message_ref:
        msg.external_message_ref = body.external_message_ref
    msg.delivery_status = body.delivery_status
    msg.error_message = body.error_message
    if body.delivery_status in {"sent", "delivered", "read"} and msg.sent_at is None:
        msg.sent_at = _now_utc()
    if body.delivery_status in {"delivered", "read"}:
        msg.delivered_at = body.delivered_at or msg.delivered_at or _now_utc()
    if body.delivery_status == "read":
        msg.read_at = body.read_at or msg.read_at or _now_utc()
    if body.provider_payload:
        msg.payload = {
            **_as_dict(msg.payload),
            "provider_callback": body.provider_payload,
        }
    await db.commit()
    await db.refresh(msg)
    return _message_out(msg)


@router.get(
    "/scheduler/status",
    response_model=CommunicationSchedulerStatusOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_communications_scheduler_status(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationSchedulerStatusOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        feature="communicationsAdmin",
    )
    data = scheduler_runtime_status()
    return CommunicationSchedulerStatusOut(**data)


@router.post(
    "/scheduler/run-now",
    response_model=CommunicationSchedulerRunNowResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def run_communications_scheduler_now(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationSchedulerRunNowResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        feature="communicationsAdmin",
    )
    data = await run_scheduler_tick_once()
    return CommunicationSchedulerRunNowResponse(
        ok=True, status=CommunicationSchedulerStatusOut(**data)
    )


@router.post(
    "/email/worker/dispatch",
    response_model=CommunicationDispatchQueuedResponse,
)
async def run_email_dispatch_worker(
    body: CommunicationEmailWorkerDispatchRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationDispatchQueuedResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(
        db, tenant_id=tenant_id, current_user=current_user, feature="email"
    )
    return await dispatch_queued_messages(
        CommunicationDispatchQueuedRequest(
            limit=body.limit,
            only_email=True,
            mark_delivered=body.mark_delivered,
            simulate_failure=False,
        ),
        db_tenant=db_tenant,
        current_user=current_user,
    )
