from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.reminder import Reminder
from backend.app.services import reminder_tasks

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "custom"
    entity_type: str = "custom"
    entity_id: Optional[str] = None
    due_at: datetime
    remind_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    source: Optional[str] = None
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = Field(default="normal")
    channel: Optional[str] = Field(default="internal")
    recurrence_json: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ReminderUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    remind_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    source: Optional[str] = None
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = None
    channel: Optional[str] = None
    message: Optional[str] = None


class SnoozeRequest(BaseModel):
    minutes: Optional[int] = None
    new_remind_at: Optional[datetime] = None


class ReminderOut(BaseModel):
    id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    type: str
    entity_type: str
    entity_id: str
    owner_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = None
    channel: Optional[str] = None
    status: str
    due_at: datetime
    remind_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    source: Optional[str] = None
    snoozed_until: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recurrence_json: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, reminder: Reminder) -> "ReminderOut":
        return cls(
            id=UUID(reminder.id),
            title=reminder.title,
            description=reminder.description,
            type=reminder.type,
            entity_type=reminder.entity_type,
            entity_id=reminder.entity_id,
            owner_id=UUID(reminder.owner_id) if reminder.owner_id else None,
            assignee_id=UUID(reminder.assignee_id) if reminder.assignee_id else None,
            priority=reminder.priority,
            channel=reminder.channel,
            status=reminder.status,
            due_at=reminder.due_at,
            remind_at=reminder.remind_at,
            duration_minutes=reminder.duration_minutes,
            source=reminder.source,
            snoozed_until=reminder.snoozed_until,
            completed_at=reminder.completed_at,
            recurrence_json=reminder.recurrence_json,
            payload=reminder.payload or {},
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
        )


class ReminderListResponse(BaseModel):
    items: List[ReminderOut]


class BulkReminderCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "custom"
    entity_type: str = "custom"
    entity_ids: List[str]
    due_at: datetime
    remind_at: Optional[datetime] = None
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = Field(default="normal")
    channel: Optional[str] = Field(default="internal")
    recurrence_json: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class BulkReminderCreateResult(BaseModel):
    entity_id: str
    ok: bool
    reminder_id: Optional[UUID] = None
    error: Optional[str] = None


class BulkReminderCreateResponse(BaseModel):
    results: List[BulkReminderCreateResult]


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderCreateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderOut:
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.create_reminder(
        db,
        tenant_id=str(tenant_id),
        actor_id=str(current_user.sub),
        payload=body.model_dump(),
    )
    await db.commit()
    await db.refresh(reminder)
    return ReminderOut.from_model(reminder)


@router.post("/bulk", response_model=BulkReminderCreateResponse)
async def bulk_create_reminders(
    body: BulkReminderCreateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> BulkReminderCreateResponse:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    actor_id = str(current_user.sub)
    results: List[BulkReminderCreateResult] = []
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
                    "assignee_id": body.assignee_id,
                    "priority": body.priority,
                    "channel": body.channel,
                    "recurrence_json": body.recurrence_json,
                    "payload": body.payload,
                },
            )
            results.append(
                BulkReminderCreateResult(
                    entity_id=eid,
                    ok=True,
                    reminder_id=UUID(reminder.id),
                )
            )
        except Exception as e:
            results.append(BulkReminderCreateResult(entity_id=eid, ok=False, error=str(e)))
    await db.commit()
    return BulkReminderCreateResponse(results=results)


@router.get("", response_model=ReminderListResponse)
async def list_reminders(
    status_filter: Optional[List[str]] = Query(default=None),
    type_filter: Optional[List[str]] = Query(default=None),
    assignee_id: Optional[UUID] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    due_from: Optional[datetime] = Query(default=None),
    due_to: Optional[datetime] = Query(default=None),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderListResponse:
    db, tenant_id = db_tenant
    entity = None
    if entity_type and entity_id:
        entity = (entity_type, entity_id)
    due_range = None
    if due_from or due_to:
        due_range = (due_from or None, due_to or None)
    reminders = await reminder_tasks.list_reminders(
        db,
        tenant_id=str(tenant_id),
        assignee_id=str(assignee_id) if assignee_id else str(current_user.sub),
        entity=entity,
        status_in=status_filter or None,
        type_in=type_filter or None,
        due_range=due_range,
    )
    return ReminderListResponse(items=[ReminderOut.from_model(r) for r in reminders])


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: UUID,
    body: ReminderUpdateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderOut:
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.update_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(reminder_id),
        actor_id=str(current_user.sub),
        role=current_user.role,
        payload=body.model_dump(exclude_none=True),
    )
    await db.commit()
    await db.refresh(reminder)
    return ReminderOut.from_model(reminder)


@router.post("/{reminder_id}/complete", response_model=ReminderOut)
async def complete_reminder(
    reminder_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderOut:
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.complete_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(reminder_id),
        actor_id=str(current_user.sub),
        role=current_user.role,
    )
    await db.commit()
    await db.refresh(reminder)
    return ReminderOut.from_model(reminder)


@router.post("/{reminder_id}/snooze", response_model=ReminderOut)
async def snooze_reminder(
    reminder_id: UUID,
    body: SnoozeRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderOut:
    db, tenant_id = db_tenant
    reminder = await reminder_tasks.snooze_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(reminder_id),
        actor_id=str(current_user.sub),
        role=current_user.role,
        minutes=body.minutes,
        new_remind_at=body.new_remind_at,
    )
    await db.commit()
    await db.refresh(reminder)
    return ReminderOut.from_model(reminder)


@router.post("/run-delivery")
async def run_delivery(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> Dict[str, Any]:
    db, tenant_id = db_tenant
    delivered = await reminder_tasks.deliver_due_reminders(db, tenant_id=str(tenant_id))
    if delivered:
        await db.commit()
    return {"delivered": delivered}


@router.post("/run-overdue")
async def run_overdue(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> Dict[str, Any]:
    db, tenant_id = db_tenant
    updated = await reminder_tasks.mark_overdue_reminders(db, tenant_id=str(tenant_id))
    if updated:
        await db.commit()
    return {"updated": updated}
