"""C0.3 — operator delivery diagnostics + provider delivery callbacks.

Endpoints:

* GET  /communications/messages/{message_id}/delivery-diagnostics
* POST /communications/messages/{message_id}/delivery-retry
* POST /communications/public/delivery-callback/{provider}
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.communications.delivery_diagnostics import (
    apply_delivery_callback,
    get_delivery_diagnostics,
    request_manual_retry,
)
from backend.app.core.audit_events import AuditEventType
from backend.app.db.deps import get_db, get_db_with_tenant
from backend.app.models.communication import CommunicationMessage
from backend.app.services.audit import log_audit_event
from backend.app.services.communications_access import assert_comm_feature_access

from .._helpers.access import _feature_for_channel, _get_tenant_or_404

router = APIRouter(tags=["communications"])


class DeliveryDiagnosticsOut(BaseModel):
    message_id: str
    delivery_id: str | None = None
    status: str
    last_attempt: Dict[str, Any] = Field(default_factory=dict)
    next_retry_at: str | None = None
    provider_reference: str | None = None
    timeline: list[Dict[str, Any]] = Field(default_factory=list)


class DeliveryRetryOut(BaseModel):
    allowed: bool
    scheduled: bool = False
    reason_code: str | None = None
    permanent_failure: bool | None = None
    exhausted: bool | None = None
    next_retry_at: str | None = None
    message_id: str | None = None
    detail: str | None = None


class DeliveryCallbackIn(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=36)
    payload: Dict[str, Any] = Field(default_factory=dict)
    provider_account_id: str | None = Field(default=None, max_length=64)
    delivery_id: str | None = Field(default=None, max_length=36)
    message_id: str | None = Field(default=None, max_length=36)


class DeliveryCallbackOut(BaseModel):
    status: str
    delivery_id: str | None = None
    message_id: str | None = None
    unresolved_id: str | None = None
    provider_event_id: str | None = None
    canonical_status: str | None = None
    applied: bool | None = None
    idempotent_replay: bool = False


@router.get(
    "/messages/{message_id}/delivery-diagnostics",
    response_model=DeliveryDiagnosticsOut,
)
async def get_message_delivery_diagnostics(
    message_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> DeliveryDiagnosticsOut:
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
    view = await get_delivery_diagnostics(
        db, tenant_id=tenant_id, message_id=message_id
    )
    if view is None:
        raise HTTPException(status_code=404, detail="Diagnostics not found")
    data = view.to_dict()
    return DeliveryDiagnosticsOut(
        message_id=data["message_id"],
        delivery_id=data.get("delivery_id"),
        status=data["status"],
        last_attempt=data.get("last_attempt") or {},
        next_retry_at=data.get("next_retry_at"),
        provider_reference=data.get("provider_reference"),
        timeline=list(data.get("timeline") or []),
    )


@router.post(
    "/messages/{message_id}/delivery-retry",
    response_model=DeliveryRetryOut,
)
async def post_message_delivery_retry(
    message_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> DeliveryRetryOut:
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
    actor = str(getattr(current_user, "sub", "") or "").strip() or None
    decision = await request_manual_retry(
        db,
        tenant_id=tenant_id,
        message_id=message_id,
        actor_user_id=actor,
    )
    if decision.get("allowed") and decision.get("scheduled"):
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.communication_delivery_retry_manual,
            entity_type="communication_message",
            entity_id=message_id,
            actor_id=actor,
            payload={
                "message_id": message_id,
                "reason_code": decision.get("reason_code"),
                "source": "delivery_diagnostics.manual_retry",
            },
        )
        await db.commit()
    elif not decision.get("allowed"):
        await db.rollback()
    else:
        await db.commit()
    return DeliveryRetryOut(
        allowed=bool(decision.get("allowed")),
        scheduled=bool(decision.get("scheduled")),
        reason_code=decision.get("reason_code"),
        permanent_failure=decision.get("permanent_failure"),
        exhausted=decision.get("exhausted"),
        next_retry_at=decision.get("next_retry_at"),
        message_id=decision.get("message_id") or message_id,
        detail=decision.get("reason"),
    )


@router.post(
    "/public/delivery-callback/{provider}",
    response_model=DeliveryCallbackOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def public_delivery_callback(
    provider: str,
    body: DeliveryCallbackIn,
    db: AsyncSession = Depends(get_db),
) -> DeliveryCallbackOut:
    """Unified provider delivery receipt ingress (C0.3 platform path)."""
    tenant_id = str(body.tenant_id).strip()
    if not tenant_id:
        raise HTTPException(status_code=422, detail="tenant_id required")
    result = await apply_delivery_callback(
        db,
        tenant_id=tenant_id,
        provider=provider,
        payload=dict(body.payload or {}),
        provider_account_id=body.provider_account_id,
        delivery_id=body.delivery_id,
        message_id=body.message_id,
    )
    await db.commit()
    return DeliveryCallbackOut(
        status=str(result.get("status") or "unknown"),
        delivery_id=result.get("delivery_id"),
        message_id=result.get("message_id"),
        unresolved_id=result.get("unresolved_id"),
        provider_event_id=result.get("provider_event_id"),
        canonical_status=result.get("canonical_status"),
        applied=result.get("applied"),
        idempotent_replay=bool(result.get("idempotent_replay")),
    )
