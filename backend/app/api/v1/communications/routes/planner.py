"""Planner / availability / time-off endpoints for the communications API.

Endpoints (URL paths preserved as registered in the parent router):

* GET    /communications/time-off/requests
* POST   /communications/time-off/requests
* POST   /communications/time-off/requests/{id}/cancel
* POST   /communications/time-off/requests/{id}/decision
* GET    /communications/availability/working-hours
* PUT    /communications/availability/working-hours
* GET    /communications/planner/events
* GET    /communications/planner/events/{id}
* POST   /communications/planner/events
* PATCH  /communications/planner/events/{id}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import (
    CommunicationPlannerEvent,
    CommunicationTimeOffRequest,
)
from backend.app.models.calendar_integration import CalendarItem
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.services.candidate_lifecycle import (
    exclude_completed_candidate_entities_clause,
    silenced_candidate_ids_subquery,
)
from backend.app.services.lead_lifecycle import (
    exclude_completed_lead_entities_clause,
)
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.timeoff_cleanup import (
    cancel_assignee_schedule_during_timeoff,
)
from backend.app.services.working_hours_window import (
    is_within_working_hours,
    schedule_applies,
)
from backend.app.services.notification_settings_v1 import normalize_notification_settings_v1
from backend.app.services.team_assignee_auto import (
    merge_assignee_resolution,
    resolve_assignee_id_with_queue_fallback,
    smart_assignee_load_context,
)

from .._helpers.access import (
    _get_tenant_or_404,
    _require_any_comm_feature,
    _require_comm_feature,
)
from .._helpers.dto import _planner_event_out, _timeoff_out
from .._helpers.utils import _as_dict, _now_utc
from .._helpers.working_hours import (
    _normalize_working_hours,
    _partial_day_blocks_now,
    _validate_iso_date_range,
)
from ..schemas import (
    CommunicationPlannerEventCreate,
    CommunicationPlannerEventListResponse,
    CommunicationPlannerEventOut,
    CommunicationPlannerEventPatch,
    TimeOffRequestCancel,
    TimeOffRequestCreate,
    TimeOffRequestDecision,
    TimeOffRequestListResponse,
    TimeOffRequestOut,
    NotificationSettingsIn,
    NotificationSettingsOut,
    WorkingHoursScheduleIn,
    WorkingHoursScheduleOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["communications"])

_TIMEOFF_ROLES = (
    Role.administrator,
    Role.supervisor,
    Role.recruiter,
    Role.client_manager,
    Role.client_processor,
)

_PLANNER_SYNCABLE_KINDS = {"meeting", "call", "task", "followup"}


def _planner_kind_syncable(kind: str | None) -> bool:
    return str(kind or "").strip().lower() in _PLANNER_SYNCABLE_KINDS


def _planner_calendar_payload(planner_event: CommunicationPlannerEvent) -> dict[str, Any]:
    source_payload = dict(planner_event.payload or {}) if isinstance(planner_event.payload, dict) else {}
    out: dict[str, Any] = {
        "created_from": "communications_planner",
        "planner_event_id": planner_event.id,
    }
    for key in (
        "location",
        "meeting_location",
        "attendees",
        "reminder_minutes",
        "recurrence",
        "microsoft_recurrence",
        "provider_overrides",
        "meeting_link",
        "is_online_meeting",
        "online_meeting_provider",
        "visibility",
        "transparency",
        "google_conference_data",
    ):
        if key in source_payload:
            out[key] = source_payload.get(key)
    return out


async def _planner_sync_create_calendar_item(
    db: AsyncSession,
    *,
    tenant_id: str,
    planner_event: CommunicationPlannerEvent,
    actor_user_id: str | None,
) -> str | None:
    from backend.app.api.v1.calendar import _sync_item_create_to_provider

    payload = dict(planner_event.payload or {})
    if not _planner_kind_syncable(planner_event.kind):
        payload.pop("calendar_item_id", None)
        payload["provider_sync"] = {"skipped": True, "reason": "planner_kind_not_syncable", "kind": planner_event.kind}
        planner_event.payload = payload
        return None
    existing_id = str(payload.get("calendar_item_id") or "").strip()
    if existing_id:
        return existing_id

    item = CalendarItem(
        tenant_id=tenant_id,
        owner_id=actor_user_id,
        assignee_id=planner_event.assignee_id,
        kind=(planner_event.kind or "event"),
        status="cancelled" if str(planner_event.status or "").lower() == "cancelled" else "scheduled",
        title=planner_event.title,
        description=planner_event.description,
        timezone="UTC",
        starts_at=planner_event.start_at,
        ends_at=planner_event.end_at,
        all_day=bool(planner_event.all_day),
        linked_entity_type=planner_event.entity_type,
        linked_entity_id=planner_event.entity_id,
        source="hostflow",
        payload=_planner_calendar_payload(planner_event),
    )
    db.add(item)
    await db.flush()
    sync_report = await _sync_item_create_to_provider(db, tenant_id=tenant_id, item=item)
    item.payload = {**dict(item.payload or {}), "provider_sync": sync_report}

    payload["calendar_item_id"] = item.id
    payload["provider_sync"] = sync_report
    planner_event.payload = payload
    return str(item.id)


async def _planner_sync_patch_calendar_item(
    db: AsyncSession,
    *,
    tenant_id: str,
    planner_event: CommunicationPlannerEvent,
    actor_user_id: str | None,
) -> None:
    from backend.app.api.v1.calendar import _sync_item_cancel_to_provider, _sync_item_update_to_provider

    payload = dict(planner_event.payload or {})
    calendar_item_id = str(payload.get("calendar_item_id") or "").strip()
    if not _planner_kind_syncable(planner_event.kind):
        if calendar_item_id:
            item = await db.get(CalendarItem, calendar_item_id)
            if item is not None and str(item.tenant_id) == tenant_id and str(item.status or "").lower() != "cancelled":
                item.status = "cancelled"
                sync_report = await _sync_item_cancel_to_provider(db, tenant_id=tenant_id, item=item)
                payload["provider_sync"] = sync_report
        payload.pop("calendar_item_id", None)
        payload["provider_sync"] = {
            **dict(payload.get("provider_sync") or {}),
            "skipped": True,
            "reason": "planner_kind_not_syncable",
            "kind": planner_event.kind,
        }
        planner_event.payload = payload
        return
    if not calendar_item_id:
        calendar_item_id = str(
            await _planner_sync_create_calendar_item(
                db,
                tenant_id=tenant_id,
                planner_event=planner_event,
                actor_user_id=actor_user_id,
            )
            or ""
        )
    if not calendar_item_id:
        return

    item = await db.get(CalendarItem, calendar_item_id)
    if item is None or str(item.tenant_id) != tenant_id:
        payload.pop("calendar_item_id", None)
        planner_event.payload = payload
        return

    item.title = planner_event.title
    item.description = planner_event.description
    item.kind = planner_event.kind or "event"
    item.starts_at = planner_event.start_at
    item.ends_at = planner_event.end_at
    item.all_day = bool(planner_event.all_day)
    item.assignee_id = planner_event.assignee_id
    item.linked_entity_type = planner_event.entity_type
    item.linked_entity_id = planner_event.entity_id
    item.owner_id = item.owner_id or actor_user_id
    item.payload = {**dict(item.payload or {}), **_planner_calendar_payload(planner_event)}

    if str(planner_event.status or "").lower() == "cancelled":
        item.status = "cancelled"
        sync_report = await _sync_item_cancel_to_provider(db, tenant_id=tenant_id, item=item)
    else:
        item.status = "scheduled"
        sync_report = await _sync_item_update_to_provider(db, tenant_id=tenant_id, item=item)

    item.payload = {**dict(item.payload or {}), "provider_sync": sync_report}
    payload["provider_sync"] = sync_report
    payload["calendar_item_id"] = item.id
    planner_event.payload = payload


async def _sync_manager_queue_availability_from_time_off(
    db: AsyncSession,
    *,
    tenant: Tenant,
    user_id: str,
    now_utc: datetime | None = None,
) -> bool:
    """Cross-domain bridge: approved time-off ↔ manager-queue availability."""
    now_utc = now_utc or _now_utc()
    today = now_utc.date().isoformat()
    current_settings = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    comm = _as_dict(current_settings.get("communications")).copy()
    queue = _as_dict(comm.get("managerQueue")).copy()
    items = queue.get("items")
    if not isinstance(items, list) or not items:
        return False

    stmt = sa.select(CommunicationTimeOffRequest).where(
        CommunicationTimeOffRequest.tenant_id == str(tenant.id),
        CommunicationTimeOffRequest.requester_user_id == str(user_id),
        CommunicationTimeOffRequest.status == "approved",
        CommunicationTimeOffRequest.start_date <= today,
        CommunicationTimeOffRequest.end_date >= today,
    ).order_by(sa.desc(CommunicationTimeOffRequest.updated_at))
    rows = (await db.execute(stmt)).scalars().all()
    active_now = None
    for row in rows:
        if _partial_day_blocks_now(row.partial_day, now_utc, _as_dict(row.payload)):
            active_now = row
            break

    changed = False
    next_items: List[Dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict) or str(raw.get("managerId") or "") != str(user_id):
            next_items.append(raw)
            continue
        item = dict(raw)
        availability = _as_dict(item.get("availability")).copy()
        note = str(availability.get("note") or "")
        auto_prefix = "[time-off-auto]"
        if active_now is not None:
            desired_note = f"{auto_prefix} approved {active_now.request_type} {active_now.start_date}..{active_now.end_date}"
            if active_now.partial_day:
                desired_note += f" ({active_now.partial_day})"
            if availability.get("state") != "offline" or note != desired_note:
                availability["state"] = "offline"
                availability["note"] = desired_note
                changed = True
        else:
            if availability.get("state") == "offline" and note.startswith(auto_prefix):
                availability["state"] = "available"
                availability["note"] = ""
                changed = True
        item["availability"] = availability
        next_items.append(item)

    if not changed:
        return False
    queue["items"] = next_items
    comm["managerQueue"] = queue
    updated_tenant_settings = dict(current_settings)
    updated_tenant_settings["communications"] = comm
    tenant.settings = updated_tenant_settings
    db.add(tenant)
    return True


@router.get(
    "/time-off/requests",
    response_model=TimeOffRequestListResponse,
    dependencies=[Depends(require_roles(*_TIMEOFF_ROLES))],
)
async def list_time_off_requests(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    mine_only: bool = Query(False),
    status_filter: List[str] | None = Query(None),
    requester_user_id: str | None = Query(None),
    approver_user_id: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "timeOffRequests"],
    )
    stmt = sa.select(CommunicationTimeOffRequest).where(CommunicationTimeOffRequest.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationTimeOffRequest).where(CommunicationTimeOffRequest.tenant_id == tenant_id)

    filters = []
    if mine_only:
        filters.append(CommunicationTimeOffRequest.requester_user_id == str(current_user.sub))
    if requester_user_id:
        filters.append(CommunicationTimeOffRequest.requester_user_id == requester_user_id)
    if approver_user_id:
        filters.append(CommunicationTimeOffRequest.approver_user_id == approver_user_id)
    if status_filter:
        filters.append(CommunicationTimeOffRequest.status.in_([str(x) for x in status_filter]))
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.desc(sa.func.coalesce(CommunicationTimeOffRequest.requested_at, CommunicationTimeOffRequest.created_at))).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return TimeOffRequestListResponse(items=[_timeoff_out(r) for r in rows], total=total)


@router.get(
    "/availability/working-hours",
    response_model=WorkingHoursScheduleOut,
    dependencies=[Depends(require_roles(*_TIMEOFF_ROLES))],
)
async def get_my_working_hours(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkingHoursScheduleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "planner", "calendar", "teamAvailability"],
    )
    user = await db.get(User, str(current_user.sub))
    if user is None or str(user.tenant_id or "") != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    extra = user.extra if isinstance(user.extra, dict) else {}
    payload = extra.get("working_hours_v1") if isinstance(extra, dict) else None
    normalized = _normalize_working_hours(payload)
    return WorkingHoursScheduleOut(tz=normalized.get("tz"), days=normalized.get("days") or [])


@router.put(
    "/availability/working-hours",
    response_model=WorkingHoursScheduleOut,
    dependencies=[Depends(require_roles(*_TIMEOFF_ROLES))],
)
async def upsert_my_working_hours(
    body: WorkingHoursScheduleIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkingHoursScheduleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "planner", "calendar", "teamAvailability"],
    )
    user = await db.get(User, str(current_user.sub))
    if user is None or str(user.tenant_id or "") != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    normalized = _normalize_working_hours(body.model_dump(by_alias=True))
    extra = user.extra if isinstance(user.extra, dict) else {}
    extra = {**extra, "working_hours_v1": normalized}
    user.extra = extra
    await db.commit()
    return WorkingHoursScheduleOut(tz=normalized.get("tz"), days=normalized.get("days") or [])


@router.get(
    "/availability/notification-settings",
    response_model=NotificationSettingsOut,
    dependencies=[Depends(require_roles(*_TIMEOFF_ROLES))],
)
async def get_my_notification_settings(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NotificationSettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "planner", "calendar", "teamAvailability"],
    )
    user = await db.get(User, str(current_user.sub))
    if user is None or str(user.tenant_id or "") != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    extra = user.extra if isinstance(user.extra, dict) else {}
    normalized = normalize_notification_settings_v1(extra.get("notification_settings_v1"))
    return NotificationSettingsOut(**normalized)


@router.put(
    "/availability/notification-settings",
    response_model=NotificationSettingsOut,
    dependencies=[Depends(require_roles(*_TIMEOFF_ROLES))],
)
async def upsert_my_notification_settings(
    body: NotificationSettingsIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NotificationSettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "planner", "calendar", "teamAvailability"],
    )
    user = await db.get(User, str(current_user.sub))
    if user is None or str(user.tenant_id or "") != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    normalized = normalize_notification_settings_v1(body.model_dump(exclude_none=True))
    extra = user.extra if isinstance(user.extra, dict) else {}
    extra = {**extra, "notification_settings_v1": normalized}
    user.extra = extra
    await db.commit()
    return NotificationSettingsOut(**normalized)


@router.post(
    "/time-off/requests",
    response_model=TimeOffRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*_TIMEOFF_ROLES))],
)
async def create_time_off_request(
    body: TimeOffRequestCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "timeOffRequests"],
    )
    _validate_iso_date_range(body.start_date, body.end_date)
    now = _now_utc()
    req = CommunicationTimeOffRequest(
        tenant_id=tenant_id,
        requester_user_id=str(current_user.sub),
        requester_label=(getattr(current_user, "email", None) or str(current_user.sub)),
        approver_user_id=body.approver_user_id or current_user.supervisor_id,
        approver_label=body.approver_label,
        request_type=(body.request_type or "vacation").strip().lower(),
        status="pending",
        start_date=body.start_date.strip(),
        end_date=body.end_date.strip(),
        partial_day=(body.partial_day or "").strip() or None,
        reason=body.reason,
        requested_at=now,
        payload=_as_dict(body.payload),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return _timeoff_out(req)


@router.post(
    "/time-off/requests/{request_id}/cancel",
    response_model=TimeOffRequestOut,
    dependencies=[Depends(require_roles(*_TIMEOFF_ROLES))],
)
async def cancel_time_off_request(
    request_id: str,
    body: TimeOffRequestCancel,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["myAvailability", "timeOffRequests"],
    )
    row = await db.get(CommunicationTimeOffRequest, request_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Time-off request not found")
    is_admin_like = (current_user.role or "").strip().lower() in {Role.administrator.value, Role.supervisor.value, Role.superadmin.value}
    if str(row.requester_user_id) != str(current_user.sub) and not is_admin_like:
        raise HTTPException(status_code=403, detail="Forbidden")
    if str(row.status or "").lower() not in {"pending"}:
        raise HTTPException(status_code=409, detail="Only pending request can be cancelled")
    row.status = "cancelled"
    row.decision_note = body.reason or row.decision_note
    row.decided_at = _now_utc()
    row.updated_at = _now_utc()
    await db.commit()
    await db.refresh(row)
    return _timeoff_out(row)


@router.post(
    "/time-off/requests/{request_id}/decision",
    response_model=TimeOffRequestOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def decide_time_off_request(
    request_id: str,
    body: TimeOffRequestDecision,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> TimeOffRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="timeOffRequests")
    row = await db.get(CommunicationTimeOffRequest, request_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Time-off request not found")
    if str(row.status or "").lower() not in {"pending"}:
        raise HTTPException(status_code=409, detail="Only pending request can be decided")
    row.status = body.decision
    row.decision_note = body.decision_note
    row.approver_user_id = str(current_user.sub)
    row.approver_label = getattr(current_user, "email", None) or row.approver_label
    row.decided_at = _now_utc()
    row.updated_at = _now_utc()
    try:
        await _sync_manager_queue_availability_from_time_off(
            db,
            tenant=tenant,
            user_id=str(row.requester_user_id),
            now_utc=row.updated_at or _now_utc(),
        )
    except Exception as e:
        logger.warning("[communications:timeoff] availability sync skipped request=%s (%s)", request_id, e)
    # G-4 stage 4: on approval, cancel the requester's pending reminders
    # and active planner events that fall inside the time-off window.
    # Best-effort: failure here logs a warning and the approval still
    # commits — operators can clean up manually if needed, and the
    # auto-cancellation isn't a guarantee anyone built workflow on.
    if str(body.decision or "").strip().lower() == "approved":
        try:
            counts = await cancel_assignee_schedule_during_timeoff(
                db,
                tenant_id=tenant_id,
                assignee_id=str(row.requester_user_id),
                start_date=str(row.start_date),
                end_date=str(row.end_date),
                request_id=str(row.id),
            )
            if counts["reminders_cancelled"] or counts["planner_events_cancelled"]:
                logger.info(
                    "[communications:timeoff] auto-cancelled schedule request=%s reminders=%d planner_events=%d",
                    request_id,
                    counts["reminders_cancelled"],
                    counts["planner_events_cancelled"],
                )
        except Exception as e:
            logger.warning(
                "[communications:timeoff] schedule cleanup skipped request=%s (%s)",
                request_id,
                e,
            )
    await db.commit()
    await db.refresh(row)
    return _timeoff_out(row)


@router.get("/planner/events", response_model=CommunicationPlannerEventListResponse)
async def list_planner_events(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: List[str] | None = Query(None),
    assignee_id: str | None = Query(None),
    from_at: datetime | None = Query(None),
    to_at: datetime | None = Query(None),
    kind: str | None = Query(None),
    include_completed_entities: bool = Query(
        False,
        description=(
            "When false (default) hides planner events linked to candidates in terminal "
            "stages (rejected/declined/employed/probation_ok) or soft-deleted."
        ),
    ),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationPlannerEventListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="planner")
    stmt = sa.select(CommunicationPlannerEvent).where(CommunicationPlannerEvent.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(CommunicationPlannerEvent).where(CommunicationPlannerEvent.tenant_id == tenant_id)
    filters = []
    if status_filter:
        filters.append(CommunicationPlannerEvent.status.in_([str(x) for x in status_filter]))
    if assignee_id:
        filters.append(CommunicationPlannerEvent.assignee_id == assignee_id)
    if kind:
        filters.append(CommunicationPlannerEvent.kind == kind)
    if from_at:
        filters.append(sa.func.coalesce(CommunicationPlannerEvent.end_at, CommunicationPlannerEvent.start_at) >= from_at)
    if to_at:
        filters.append(CommunicationPlannerEvent.start_at <= to_at)
    # G-2: drop events tied to silenced candidates. Planner has TWO ways to link a candidate
    # (`linked_candidate_id` *or* `entity_type='candidate'/entity_id=<cand>`), so we apply
    # both checks: skip the row if either join hits the silenced-candidates subquery.
    if not include_completed_entities:
        silenced = silenced_candidate_ids_subquery(tenant_id)
        filters.append(
            sa.and_(
                sa.or_(
                    CommunicationPlannerEvent.linked_candidate_id.is_(None),
                    sa.not_(CommunicationPlannerEvent.linked_candidate_id.in_(silenced)),
                ),
                exclude_completed_candidate_entities_clause(
                    tenant_id,
                    entity_type_col=CommunicationPlannerEvent.entity_type,
                    entity_id_col=CommunicationPlannerEvent.entity_id,
                ),
                exclude_completed_lead_entities_clause(
                    tenant_id,
                    entity_type_col=CommunicationPlannerEvent.entity_type,
                    entity_id_col=CommunicationPlannerEvent.entity_id,
                ),
            )
        )
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.asc(CommunicationPlannerEvent.start_at), sa.asc(CommunicationPlannerEvent.created_at)).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationPlannerEventListResponse(items=[_planner_event_out(r) for r in rows], total=total)


@router.get("/planner/events/{event_id}", response_model=CommunicationPlannerEventOut)
async def get_planner_event(
    event_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationPlannerEventOut:
    """Single planner row for calendar deep-links (G-6: ``/app/calendar?event_id=``)."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="planner")
    row = await db.get(CommunicationPlannerEvent, event_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Planner event not found")
    return _planner_event_out(row)


# G-4 stage 3: tenant setting that enables server-side rejection of
# planner events scheduled outside the assignee's working hours.
# Default OFF to preserve current behaviour. Path mirrors the reminder
# shift policy:
#   tenant.settings["planner"]["enforce_working_hours"]: bool
# The schema-level `allow_outside_hours=True` flag is the per-event
# override — operators consciously schedule the after-hours interview
# instead of being silently blocked. The flag is consumed here and not
# persisted on the row.
_PLANNER_ENFORCE_PATH = ("planner", "enforce_working_hours")


async def _tenant_enforces_planner_working_hours(
    db: AsyncSession, *, tenant_id: str
) -> bool:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or not isinstance(tenant.settings, dict):
        return False
    cursor: Any = tenant.settings
    for key in _PLANNER_ENFORCE_PATH:
        if not isinstance(cursor, dict):
            return False
        cursor = cursor.get(key)
    return bool(cursor)


async def _assert_within_working_hours_or_overridden(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: str | None,
    start_at: datetime | None,
    end_at: datetime | None,
    allow_outside_hours: bool,
) -> None:
    """Reject the request if `start_at`/`end_at` fall outside the
    assignee's `working_hours_v1` schedule, unless the caller passed
    `allow_outside_hours=True`. Silent no-op when:
      * tenant hasn't enabled enforcement,
      * the planner event has no assignee (org-wide / unassigned),
      * the assignee has no schedule configured,
      * the override flag is set.

    Both `start_at` AND `end_at` are checked: a meeting that starts at
    16:30 and runs until 18:30 is partially outside hours and should be
    flagged. The 422 message names which side breached, so the operator
    can adjust without guessing."""
    if not assignee_id or start_at is None:
        return
    if allow_outside_hours:
        return
    if not await _tenant_enforces_planner_working_hours(db, tenant_id=tenant_id):
        return
    user = await db.get(User, str(assignee_id))
    if user is None:
        return
    extra = user.extra if isinstance(user.extra, dict) else {}
    if not schedule_applies(extra):
        return
    if not is_within_working_hours(extra, start_at):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "outside_working_hours",
                "message": "start_at is outside the assignee's working hours",
                "field": "start_at",
                "hint": "Pass allow_outside_hours=true to override.",
            },
        )
    if end_at is not None and not is_within_working_hours(extra, end_at):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "outside_working_hours",
                "message": "end_at is outside the assignee's working hours",
                "field": "end_at",
                "hint": "Pass allow_outside_hours=true to override.",
            },
        )


@router.post("/planner/events", response_model=CommunicationPlannerEventOut, status_code=status.HTTP_201_CREATED)
async def create_planner_event(
    body: CommunicationPlannerEventCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationPlannerEventOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="planner")
    if body.end_at and body.end_at < body.start_at:
        raise HTTPException(status_code=422, detail="end_at must be greater than or equal to start_at")
    start_at_norm = body.start_at if body.start_at.tzinfo else body.start_at.replace(tzinfo=timezone.utc)
    end_at_norm = (
        body.end_at if (body.end_at and body.end_at.tzinfo)
        else (body.end_at.replace(tzinfo=timezone.utc) if body.end_at else None)
    )
    eff_assignee, assignee_resolution = await resolve_assignee_id_with_queue_fallback(
        db,
        tenant_id=tenant_id,
        assignee_id=body.assignee_id,
        allow_unavailable_assignee=body.allow_unavailable_assignee,
        load_context=await smart_assignee_load_context(
            db, tenant_id=tenant_id, anchor=start_at_norm
        ),
    )
    plan_payload = merge_assignee_resolution(_as_dict(body.payload), assignee_resolution)
    await _assert_within_working_hours_or_overridden(
        db,
        tenant_id=tenant_id,
        assignee_id=eff_assignee,
        start_at=start_at_norm,
        end_at=end_at_norm,
        allow_outside_hours=body.allow_outside_hours,
    )
    row = CommunicationPlannerEvent(
        tenant_id=tenant_id,
        title=body.title.strip(),
        description=body.description,
        kind=(body.kind or "task").strip().lower(),
        status=(body.status or "planned").strip().lower(),
        priority=(body.priority or "normal").strip().lower(),
        start_at=start_at_norm,
        end_at=end_at_norm,
        all_day=bool(body.all_day),
        owner_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        assignee_id=eff_assignee,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        linked_candidate_id=body.linked_candidate_id,
        linked_company_id=body.linked_company_id,
        source=(body.source or "manual").strip().lower(),
        payload=plan_payload,
    )
    db.add(row)
    await db.flush()
    await _planner_sync_create_calendar_item(
        db,
        tenant_id=tenant_id,
        planner_event=row,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )
    await db.commit()
    await db.refresh(row)
    return _planner_event_out(row)


@router.patch("/planner/events/{event_id}", response_model=CommunicationPlannerEventOut)
async def patch_planner_event(
    event_id: str,
    body: CommunicationPlannerEventPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationPlannerEventOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="planner")
    row = await db.get(CommunicationPlannerEvent, event_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Planner event not found")

    patch = body.model_dump(exclude_unset=True)
    for key in ["title", "description", "kind", "status", "priority", "all_day", "assignee_id", "entity_type", "entity_id", "linked_candidate_id", "linked_company_id"]:
        if key in patch:
            value = patch[key]
            if key in {"kind", "status", "priority"} and isinstance(value, str):
                value = value.strip().lower()
            if key == "title" and isinstance(value, str):
                value = value.strip()
            setattr(row, key, value)
    if "start_at" in patch:
        dt = patch["start_at"]
        row.start_at = dt if (dt is None or dt.tzinfo) else dt.replace(tzinfo=timezone.utc)
    if "end_at" in patch:
        dt = patch["end_at"]
        row.end_at = dt if (dt is None or dt.tzinfo) else dt.replace(tzinfo=timezone.utc)
    if row.end_at and row.end_at < row.start_at:
        raise HTTPException(status_code=422, detail="end_at must be greater than or equal to start_at")
    # G-4 stage 3: re-validate working hours when start/end/assignee
    # changed (or any combination). Skipping the check on patches that
    # don't touch those fields keeps the common case fast — no DB
    # roundtrip to the User table just to update `description`.
    assignee_resolution: dict | None = None
    if "start_at" in patch or "end_at" in patch or "assignee_id" in patch:
        eff_id, assignee_resolution = await resolve_assignee_id_with_queue_fallback(
            db,
            tenant_id=tenant_id,
            assignee_id=row.assignee_id,
            allow_unavailable_assignee=body.allow_unavailable_assignee,
            load_context=await smart_assignee_load_context(
                db, tenant_id=tenant_id, anchor=row.start_at
            ),
        )
        if eff_id is not None:
            row.assignee_id = eff_id
        await _assert_within_working_hours_or_overridden(
            db,
            tenant_id=tenant_id,
            assignee_id=row.assignee_id,
            start_at=row.start_at,
            end_at=row.end_at,
            allow_outside_hours=body.allow_outside_hours,
        )
    if "payload" in patch and patch["payload"] is not None:
        row.payload = _as_dict(patch["payload"])
    if assignee_resolution:
        row.payload = merge_assignee_resolution(_as_dict(row.payload), assignee_resolution)
    await _planner_sync_patch_calendar_item(
        db,
        tenant_id=tenant_id,
        planner_event=row,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )
    row.updated_at = _now_utc()
    await db.commit()
    await db.refresh(row)
    return _planner_event_out(row)
