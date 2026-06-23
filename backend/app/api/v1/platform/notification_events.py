"""Notification event registry read/update API (P2)."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.auth.deps import require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.document_expiry_notifications.constants import (
    EVENT_STATUS_IGNORED,
    EVENT_STATUS_OPEN,
    EVENT_STATUS_RESOLVED,
    SOURCE_LAYER,
    VALID_EVENT_STATUSES,
)
from backend.app.document_expiry_notifications.event_registry import (
    get_notification_event,
    list_notification_events,
    notification_event_to_dict,
    update_notification_event_status,
)
from backend.app.models.notification_event import NotificationEvent

ADMIN_ROLES = ("administrator", "superadmin", "supervisor")

router = APIRouter(
    prefix="/platform/notification-events",
    tags=["notification-events"],
    redirect_slashes=False,
)


class NotificationEventOut(BaseModel):
    id: str
    tenant_id: str
    event_key: str
    evaluation_version: str
    event_code: str
    source_layer: str
    owner_type: str
    owner_id: str
    document_id: Optional[str] = None
    document_type_code: Optional[str] = None
    severity: str
    document_runtime: dict
    metadata: dict = Field(default_factory=dict)
    evaluated_at: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class NotificationEventStatusIn(BaseModel):
    status: Literal["open", "resolved", "ignored"]


def _row_to_out(row: NotificationEvent) -> NotificationEventOut:
    payload = notification_event_to_dict(row)
    return NotificationEventOut(**payload)


@router.get(
    "",
    response_model=list[NotificationEventOut],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
async def list_open_notification_events(
    db_tenant: tuple = Depends(get_db_with_tenant),
    status: str = Query(default=EVENT_STATUS_OPEN),
    source_layer: Optional[str] = Query(default=SOURCE_LAYER),
    event_code: Optional[str] = Query(default=None, alias="event_type"),
) -> list[NotificationEventOut]:
    db, tenant_id = db_tenant
    normalized_status = str(status or EVENT_STATUS_OPEN).strip().lower()
    if normalized_status not in VALID_EVENT_STATUSES:
        raise HTTPException(status_code=422, detail=f"Unsupported status filter: {status}")

    normalized_source_layer = str(source_layer).strip() if source_layer is not None else None
    normalized_event_code = str(event_code).strip() if event_code else None

    rows = await list_notification_events(
        db,
        str(tenant_id),
        status=normalized_status,
        source_layer=normalized_source_layer or None,
        event_code=normalized_event_code,
    )
    return [_row_to_out(row) for row in rows]


@router.get(
    "/{event_id}",
    response_model=NotificationEventOut,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
async def get_notification_event_detail(
    event_id: str,
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> NotificationEventOut:
    db, tenant_id = db_tenant
    row = await get_notification_event(db, str(tenant_id), event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification event not found")
    return _row_to_out(row)


@router.patch(
    "/{event_id}/status",
    response_model=NotificationEventOut,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
async def patch_notification_event_status(
    event_id: str,
    body: NotificationEventStatusIn,
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> NotificationEventOut:
    db, tenant_id = db_tenant
    if body.status not in {EVENT_STATUS_OPEN, EVENT_STATUS_RESOLVED, EVENT_STATUS_IGNORED}:
        raise HTTPException(status_code=422, detail=f"Unsupported status: {body.status}")

    row = await update_notification_event_status(
        db,
        str(tenant_id),
        event_id,
        status=body.status,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Notification event not found")

    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)
