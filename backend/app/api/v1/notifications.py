from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, get_current_user, require_roles
from backend.app.auth.deps import UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.services import user_notifications
from backend.app.services.user_notifications import notification_out_priority
from backend.app.services.notification_templates import list_notification_templates

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationTemplateChannelOut(BaseModel):
    channel: str
    template_key: str
    subject_key: Optional[str] = None
    body_key: Optional[str] = None
    default_subject: Optional[str] = None
    default_body: Optional[str] = None


class NotificationTemplateOut(BaseModel):
    slug: str
    event_type: str
    description: str
    offset_hours: Optional[int] = None
    schedule_key: Optional[str] = None
    variables: List[str] = Field(default_factory=list)
    localization_keys: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    channels: List[NotificationTemplateChannelOut] = Field(default_factory=list)
    channel_templates: Dict[str, NotificationTemplateChannelOut] = Field(default_factory=dict)


class NotificationTemplateListResponse(BaseModel):
    items: List[NotificationTemplateOut]


class NotificationOut(BaseModel):
    id: UUID
    event_type: str
    channel: str
    priority: str = Field(description="UOS attention tier: critical | high | normal (canonical).")
    payload: Dict[str, Any] = Field(default_factory=dict)
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    is_read: bool
    created_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    items: List[NotificationOut]


class NotificationReadRequest(BaseModel):
    ids: Optional[List[UUID]] = None
    mark_all: bool = False


class NotificationReconcileResponse(BaseModel):
    cleaned: int


class NotificationTenantReconcileResponse(BaseModel):
    users_processed: int
    cleaned: int


@router.get("/templates", response_model=NotificationTemplateListResponse)
async def list_notification_templates_endpoint() -> NotificationTemplateListResponse:
    templates = list_notification_templates()
    items: List[NotificationTemplateOut] = []
    for template in templates:
        localization_keys = set()
        channel_map: Dict[str, NotificationTemplateChannelOut] = {}
        for channel_def in template.channels:
            localization_keys.update(
                key
                for key in (
                    channel_def.template_key,
                    channel_def.subject_key,
                    channel_def.body_key,
                )
                if key
            )
            channel_map[channel_def.channel] = NotificationTemplateChannelOut(
                channel=channel_def.channel,
                template_key=channel_def.template_key,
                subject_key=channel_def.subject_key,
                body_key=channel_def.body_key,
                default_subject=channel_def.default_subject,
                default_body=channel_def.default_body,
            )
        items.append(
            NotificationTemplateOut(
                slug=template.slug,
                event_type=template.event_type,
                description=template.description,
                offset_hours=template.offset_hours,
                schedule_key=template.schedule_key,
                variables=list(template.variables),
                localization_keys=sorted(localization_keys),
                metadata=dict(template.metadata or {}),
                channels=list(channel_map.values()),
                channel_templates=channel_map,
            )
        )
    return NotificationTemplateListResponse(items=items)


@router.get("", response_model=NotificationListResponse)
@router.get("/", response_model=NotificationListResponse, include_in_schema=False)
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    include_read: bool = Query(False),
    scope: Literal["all", "direct"] = Query("direct"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NotificationListResponse:
    db, tenant_id = db_tenant
    cleaned = await user_notifications.cleanup_stale_sla_notifications(
        db,
        tenant_id=str(tenant_id),
        user_id=str(current_user.sub),
    )
    if cleaned > 0:
        await db.commit()
    notifications = await user_notifications.list_notifications(
        db,
        tenant_id=str(tenant_id),
        user_id=str(current_user.sub),
        limit=limit,
        include_read=include_read,
        scope=scope,
    )
    return NotificationListResponse(
        items=[
            NotificationOut(
                id=UUID(n.id),
                event_type=n.event_type,
                channel=n.channel,
                priority=notification_out_priority(n),
                payload=n.payload or {},
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                is_read=bool(n.is_read),
                created_at=n.created_at,
                delivered_at=n.delivered_at,
                read_at=n.read_at,
            )
            for n in notifications
        ]
    )


@router.post("/read", status_code=status.HTTP_200_OK)
async def mark_notifications_read(
    body: NotificationReadRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> Dict[str, int]:
    if not body.mark_all and not body.ids:
        raise HTTPException(status_code=400, detail="ids or mark_all required")

    db, tenant_id = db_tenant
    updated = await user_notifications.mark_notifications_read(
        db,
        tenant_id=str(tenant_id),
        user_id=str(current_user.sub),
        notification_ids=[str(i) for i in body.ids] if body.ids else None,
        mark_all=body.mark_all,
    )
    if updated > 0:
        await db.commit()
    return {"updated": updated}


@router.post("/reconcile", response_model=NotificationReconcileResponse)
async def reconcile_notifications(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NotificationReconcileResponse:
    db, tenant_id = db_tenant
    cleaned = await user_notifications.cleanup_stale_sla_notifications(
        db,
        tenant_id=str(tenant_id),
        user_id=str(current_user.sub),
    )
    if cleaned > 0:
        await db.commit()
    return NotificationReconcileResponse(cleaned=cleaned)


@router.post(
    "/reconcile-tenant",
    response_model=NotificationTenantReconcileResponse,
    dependencies=[Depends(require_roles(Role.supervisor, Role.administrator, Role.superadmin))],
)
async def reconcile_notifications_tenant(
    max_users: int = Query(2000, ge=1, le=10000),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NotificationTenantReconcileResponse:
    _ = current_user
    db, tenant_id = db_tenant
    result = await user_notifications.cleanup_stale_sla_notifications_for_tenant(
        db,
        tenant_id=str(tenant_id),
        max_users=max_users,
    )
    if int(result.get("cleaned") or 0) > 0:
        await db.commit()
    return NotificationTenantReconcileResponse(
        users_processed=int(result.get("users_processed") or 0),
        cleaned=int(result.get("cleaned") or 0),
    )
