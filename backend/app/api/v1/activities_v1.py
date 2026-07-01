from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.reminders_v2 import (
    ReminderCreateRequest as ActivityCreateRequest,
    ReminderUpdateRequest as ActivityUpdateRequest,
    SnoozeRequest as ActivitySnoozeRequest,
    ReminderOut as ActivityOut,
    ReminderListResponse as ActivityListResponse,
    _sync_reminder_create_calendar_item,
    _sync_reminder_patch_calendar_item,
)
from backend.app.services import reminder_tasks

router = APIRouter(prefix="/activities", tags=["activities"])


class BulkActivityCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "custom"
    entity_type: str = "custom"
    entity_ids: List[str]
    due_at: datetime
    remind_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    source: Optional[str] = None
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = Field(default="normal")
    channel: Optional[str] = Field(default="internal")
    recurrence_json: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class BulkActivityCreateResult(BaseModel):
    entity_id: str
    ok: bool
    activity_id: Optional[UUID] = None
    error: Optional[str] = None


class BulkActivityCreateResponse(BaseModel):
    results: List[BulkActivityCreateResult]


@router.post("/bulk", response_model=BulkActivityCreateResponse)
async def bulk_create_activities(
    body: BulkActivityCreateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> BulkActivityCreateResponse:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    actor_id = str(current_user.sub)
    results: List[BulkActivityCreateResult] = []
    for entity_id in body.entity_ids:
        eid = str(entity_id or "").strip()
        if not eid:
            continue
        try:
            reminder = await reminder_tasks.create_reminder(
                db,
                tenant_id=tenant_id_str,
                actor_id=actor_id,
                payload={
                    "title": body.title,
                    "description": body.description,
                    "type": body.type,
                    "entity_type": body.entity_type,
                    "entity_id": eid,
                    "due_at": body.due_at,
                    "remind_at": body.remind_at,
                    "duration_minutes": body.duration_minutes,
                    "source": body.source or "bulk",
                    "assignee_id": body.assignee_id,
                    "priority": body.priority,
                    "channel": body.channel,
                    "recurrence_json": body.recurrence_json,
                    "payload": body.payload,
                },
            )
            await _sync_reminder_create_calendar_item(
                db,
                tenant_id=tenant_id_str,
                reminder=reminder,
                actor_user_id=actor_id,
            )
            results.append(
                BulkActivityCreateResult(
                    entity_id=eid,
                    ok=True,
                    activity_id=UUID(reminder.id),
                )
            )
        except Exception as e:
            results.append(BulkActivityCreateResult(entity_id=eid, ok=False, error=str(e)))
    await db.commit()
    return BulkActivityCreateResponse(results=results)

@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
async def create_activity(
    body: ActivityCreateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ActivityOut:
    db, tenant_id = db_tenant
    if str(body.entity_type or "").strip().lower() == "candidate" and body.entity_id:
        from backend.app.services.candidate_operational_write import (
            ensure_candidate_operational_write_allowed,
        )

        await ensure_candidate_operational_write_allowed(
            db,
            tenant_id=str(tenant_id),
            candidate_id=str(body.entity_id),
            role=str(getattr(current_user, "role", "") or ""),
        )
    reminder = await reminder_tasks.create_reminder(
        db,
        tenant_id=str(tenant_id),
        actor_id=str(current_user.sub),
        payload=body.model_dump(),
    )
    await _sync_reminder_create_calendar_item(
        db,
        tenant_id=str(tenant_id),
        reminder=reminder,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )
    await db.commit()
    await db.refresh(reminder)
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(db, tenant_id=str(tenant_id), reminders=[reminder])
    return ActivityOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    status_filter: Optional[List[str]] = Query(default=None),
    type_filter: Optional[List[str]] = Query(default=None),
    assignee_id: Optional[UUID] = Query(default=None),
    assignee_scope: str = Query("mine", pattern="^(mine|team)$"),
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    due_from: Optional[datetime] = Query(default=None),
    due_to: Optional[datetime] = Query(default=None),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ActivityListResponse:
    db, tenant_id = db_tenant
    entity = (entity_type, entity_id) if (entity_type and entity_id) else None
    entity_type_filter = str(entity_type).strip() if entity_type and not entity_id else None
    due_range = (due_from or None, due_to or None) if (due_from or due_to) else None
    aid = reminder_tasks.resolve_assignee_for_reminder_list(
        explicit_assignee_id=str(assignee_id) if assignee_id else None,
        assignee_scope=assignee_scope,
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
    )
    reminders = await reminder_tasks.list_reminders(
        db,
        tenant_id=str(tenant_id),
        assignee_id=aid,
        entity=entity,
        entity_type_filter=entity_type_filter or None,
        status_in=status_filter or None,
        type_in=type_filter or None,
        due_range=due_range,
    )
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(db, tenant_id=str(tenant_id), reminders=reminders)
    return ActivityListResponse(
        items=[ActivityOut.from_model(r, payload_merge=merges.get(str(r.id))) for r in reminders],
    )


@router.get("/{activity_id}", response_model=ActivityOut)
async def get_activity(
    activity_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ActivityOut:
    """Fetch one activity/reminder for deep-links (e.g. ``/app/calendar?event_id=``)."""
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.get_reminder_for_actor(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(activity_id),
        actor_id=str(current_user.sub),
        role=current_user.role,
    )
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(db, tenant_id=str(tenant_id), reminders=[reminder])
    return ActivityOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.patch("/{activity_id}", response_model=ActivityOut)
async def update_activity(
    activity_id: UUID,
    body: ActivityUpdateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ActivityOut:
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.update_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(activity_id),
        actor_id=str(current_user.sub),
        role=current_user.role,
        payload=body.model_dump(exclude_none=True),
    )
    await _sync_reminder_patch_calendar_item(
        db,
        tenant_id=str(tenant_id),
        reminder=reminder,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        is_terminal=False,
    )
    await db.commit()
    await db.refresh(reminder)
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(db, tenant_id=str(tenant_id), reminders=[reminder])
    return ActivityOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.post("/{activity_id}/complete", response_model=ActivityOut)
async def complete_activity(
    activity_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ActivityOut:
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.complete_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(activity_id),
        actor_id=str(current_user.sub),
        role=current_user.role,
    )
    await _sync_reminder_patch_calendar_item(
        db,
        tenant_id=str(tenant_id),
        reminder=reminder,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        is_terminal=True,
    )
    await db.commit()
    await db.refresh(reminder)
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(db, tenant_id=str(tenant_id), reminders=[reminder])
    return ActivityOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.post("/{activity_id}/snooze", response_model=ActivityOut)
async def snooze_activity(
    activity_id: UUID,
    body: ActivitySnoozeRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ActivityOut:
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.snooze_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(activity_id),
        actor_id=str(current_user.sub),
        role=current_user.role,
        minutes=body.minutes,
        new_remind_at=body.new_remind_at,
    )
    await _sync_reminder_patch_calendar_item(
        db,
        tenant_id=str(tenant_id),
        reminder=reminder,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        is_terminal=False,
    )
    await db.commit()
    await db.refresh(reminder)
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(db, tenant_id=str(tenant_id), reminders=[reminder])
    return ActivityOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))

