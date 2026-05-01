from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.services import billing_restrictions, reminder_tasks

_SLA_REMINDER_TYPES = frozenset(
    {
        "leads_no_next_action",
        "invoice_overdue_payment",
        "uos_order_confirm",
        "uos_invoice_follow_payment",
        "uos_candidate_call",
        "uos_inbound_reply",
        "uos_client_intro",
        "uos_client_stage_follow_up",
        "uos_candidate_stage_follow_up",
        "communications_thread_escalated",
        "uos_vacancy_recruiting_follow_up",
    }
)

_REMINDER_SYNC_EXCLUDED_TYPES = frozenset(
    {
        "document_expiry",
        "document_workflow_step",
        "invoice_overdue_payment",
        "communications_thread_escalated",
    }
)


def _is_reminder_syncable(reminder: Reminder) -> bool:
    rtype = str(getattr(reminder, "type", "") or "").strip().lower()
    if not rtype:
        return True
    if rtype in _REMINDER_SYNC_EXCLUDED_TYPES:
        return False
    if rtype.startswith("uos_"):
        return False
    return True


def _to_calendar_item_times(reminder: Reminder) -> tuple[datetime, datetime]:
    start_at = reminder.due_at
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    minutes = int(getattr(reminder, "duration_minutes", 0) or 0)
    if minutes < 15:
        minutes = 30
    end_at = start_at + timedelta(minutes=minutes)
    return start_at, end_at


async def _sync_reminder_create_calendar_item(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder: Reminder,
    actor_user_id: str | None,
) -> str | None:
    if not _is_reminder_syncable(reminder):
        payload = dict(reminder.payload or {})
        payload["provider_sync"] = {"skipped": True, "reason": "reminder_type_not_syncable", "type": reminder.type}
        reminder.payload = payload
        return None
    from backend.app.api.v1.calendar import _sync_item_create_to_provider
    from backend.app.models.calendar_integration import CalendarItem

    payload = dict(reminder.payload or {})
    existing_id = str(payload.get("calendar_item_id") or "").strip()
    if existing_id:
        return existing_id
    starts_at, ends_at = _to_calendar_item_times(reminder)
    item = CalendarItem(
        tenant_id=tenant_id,
        owner_id=actor_user_id,
        assignee_id=reminder.assignee_id,
        kind="task",
        status="scheduled",
        title=(reminder.title or "Task").strip() or "Task",
        description=reminder.description,
        timezone="UTC",
        starts_at=starts_at,
        ends_at=ends_at,
        all_day=False,
        linked_entity_type=reminder.entity_type,
        linked_entity_id=reminder.entity_id,
        source="hostflow",
        payload={
            "created_from": "reminder",
            "reminder_id": reminder.id,
            "reminder_type": reminder.type,
        },
    )
    db.add(item)
    await db.flush()
    sync_report = await _sync_item_create_to_provider(db, tenant_id=tenant_id, item=item)
    item.payload = {**dict(item.payload or {}), "provider_sync": sync_report}
    payload["calendar_item_id"] = item.id
    payload["provider_sync"] = sync_report
    reminder.payload = payload
    return str(item.id)


async def _sync_reminder_patch_calendar_item(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder: Reminder,
    actor_user_id: str | None,
    is_terminal: bool = False,
) -> None:
    from backend.app.api.v1.calendar import _sync_item_cancel_to_provider, _sync_item_update_to_provider
    from backend.app.models.calendar_integration import CalendarItem

    payload = dict(reminder.payload or {})
    calendar_item_id = str(payload.get("calendar_item_id") or "").strip()
    if not _is_reminder_syncable(reminder):
        if calendar_item_id:
            item = await db.get(CalendarItem, calendar_item_id)
            if item is not None and str(item.tenant_id) == tenant_id and str(item.status or "").lower() != "cancelled":
                item.status = "cancelled"
                payload["provider_sync"] = await _sync_item_cancel_to_provider(db, tenant_id=tenant_id, item=item)
        payload.pop("calendar_item_id", None)
        payload["provider_sync"] = {
            **dict(payload.get("provider_sync") or {}),
            "skipped": True,
            "reason": "reminder_type_not_syncable",
            "type": reminder.type,
        }
        reminder.payload = payload
        return
    if not calendar_item_id:
        calendar_item_id = str(
            await _sync_reminder_create_calendar_item(
                db,
                tenant_id=tenant_id,
                reminder=reminder,
                actor_user_id=actor_user_id,
            )
            or ""
        )
    if not calendar_item_id:
        return
    item = await db.get(CalendarItem, calendar_item_id)
    if item is None or str(item.tenant_id) != tenant_id:
        payload.pop("calendar_item_id", None)
        reminder.payload = payload
        return
    starts_at, ends_at = _to_calendar_item_times(reminder)
    item.title = (reminder.title or "Task").strip() or "Task"
    item.description = reminder.description
    item.kind = "task"
    item.starts_at = starts_at
    item.ends_at = ends_at
    item.all_day = False
    item.assignee_id = reminder.assignee_id
    item.linked_entity_type = reminder.entity_type
    item.linked_entity_id = reminder.entity_id
    item.owner_id = item.owner_id or actor_user_id
    if is_terminal:
        item.status = "cancelled"
        sync_report = await _sync_item_cancel_to_provider(db, tenant_id=tenant_id, item=item)
    else:
        item.status = "scheduled"
        sync_report = await _sync_item_update_to_provider(db, tenant_id=tenant_id, item=item)
    item.payload = {**dict(item.payload or {}), "provider_sync": sync_report}
    payload["provider_sync"] = sync_report
    payload["calendar_item_id"] = item.id
    reminder.payload = payload


def reminder_sla_projection(reminder: Reminder) -> Tuple[Optional[datetime], Optional[str]]:
    """Derive SLA deadline + coarse status for UOS (no separate SLA table)."""
    if reminder.status in (ReminderStatus.done, ReminderStatus.cancelled):
        return None, "resolved"
    payload = reminder.payload if isinstance(reminder.payload, dict) else {}
    sla_due_at: Optional[datetime] = None
    raw = payload.get("sla_due_at")
    if isinstance(raw, str) and raw.strip():
        try:
            sla_due_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            sla_due_at = None
    if sla_due_at is None and reminder.type in _SLA_REMINDER_TYPES:
        sla_due_at = reminder.due_at
    if sla_due_at is None:
        return None, None
    now = datetime.now(timezone.utc)
    end = sla_due_at
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if now > end:
        return end, "overdue"
    if (end - now).total_seconds() < 24 * 3600:
        return end, "at_risk"
    return end, "on_track"

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
    allow_unavailable_assignee: bool = False
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
    allow_unavailable_assignee: bool = False


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
    sla_due_at: Optional[datetime] = None
    sla_status: Optional[str] = None

    @classmethod
    def from_model(cls, reminder: Reminder, *, payload_merge: Optional[Dict[str, Any]] = None) -> "ReminderOut":
        sla_due_at, sla_status = reminder_sla_projection(reminder)
        payload: Dict[str, Any] = dict(reminder.payload or {})
        if payload_merge:
            payload.update(payload_merge)
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
            payload=payload,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            sla_due_at=sla_due_at,
            sla_status=sla_status,
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
    allow_unavailable_assignee: bool = False
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
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
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
    return ReminderOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.post("/bulk", response_model=BulkReminderCreateResponse)
async def bulk_create_reminders(
    body: BulkReminderCreateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> BulkReminderCreateResponse:
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
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
            await _sync_reminder_create_calendar_item(
                db,
                tenant_id=tenant_id_str,
                reminder=reminder,
                actor_user_id=actor_id,
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
    assignee_scope: str = Query("mine", pattern="^(mine|team)$"),
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    due_from: Optional[datetime] = Query(default=None),
    due_to: Optional[datetime] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Search title, description, or message (substring)"),
    limit: Optional[int] = Query(default=None, ge=1, le=200),
    include_completed_entities: bool = Query(
        default=False,
        description=(
            "When false (default) hides reminders for candidates in terminal stages "
            "(rejected/declined/employed/probation_ok) or soft-deleted. Set true to see everything."
        ),
    ),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderListResponse:
    db, tenant_id = db_tenant
    entity = None
    entity_type_filter: Optional[str] = None
    if entity_type and entity_id:
        entity = (entity_type, entity_id)
    elif entity_type:
        entity_type_filter = str(entity_type).strip() or None
    due_range = None
    if due_from or due_to:
        due_range = (due_from or None, due_to or None)
    aid = reminder_tasks.resolve_assignee_for_reminder_list(
        explicit_assignee_id=str(assignee_id) if assignee_id else None,
        assignee_scope=assignee_scope,
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
    )
    q_norm = (q or "").strip()
    eff_limit = limit
    if q_norm and eff_limit is None:
        eff_limit = 80
    reminders = await reminder_tasks.list_reminders(
        db,
        tenant_id=str(tenant_id),
        assignee_id=aid,
        entity=entity,
        entity_type_filter=entity_type_filter,
        status_in=status_filter or None,
        type_in=type_filter or None,
        due_range=due_range,
        q=q_norm or None,
        limit=eff_limit,
        include_completed_entities=include_completed_entities,
    )
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(db, tenant_id=str(tenant_id), reminders=reminders)
    return ReminderListResponse(
        items=[ReminderOut.from_model(r, payload_merge=merges.get(str(r.id))) for r in reminders],
    )


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: UUID,
    body: ReminderUpdateRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderOut:
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    reminder = await reminder_tasks.update_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(reminder_id),
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
    return ReminderOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.post("/{reminder_id}/complete", response_model=ReminderOut)
async def complete_reminder(
    reminder_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderOut:
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_action_for_tenant_id(
        db,
        str(tenant_id),
        action="task_complete",
    )
    reminder = await reminder_tasks.complete_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(reminder_id),
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
    return ReminderOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.post("/{reminder_id}/snooze", response_model=ReminderOut)
async def snooze_reminder(
    reminder_id: UUID,
    body: SnoozeRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ReminderOut:
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    reminder = await reminder_tasks.snooze_reminder(
        db,
        tenant_id=str(tenant_id),
        reminder_id=str(reminder_id),
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
    return ReminderOut.from_model(reminder, payload_merge=merges.get(str(reminder.id)))


@router.post("/run-delivery")
async def run_delivery(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> Dict[str, Any]:
    db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
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
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, str(tenant_id))
    updated = await reminder_tasks.mark_overdue_reminders(db, tenant_id=str(tenant_id))
    if updated:
        await db.commit()
    return {"updated": updated}
