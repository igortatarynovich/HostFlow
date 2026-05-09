"""Availability / time-off endpoints for the communications API.

Endpoints (URL paths preserved as registered in the parent router):

* GET    /communications/time-off/requests
* POST   /communications/time-off/requests
* POST   /communications/time-off/requests/{id}/cancel
* POST   /communications/time-off/requests/{id}/decision
* GET    /communications/availability/working-hours
* PUT    /communications/availability/working-hours
* GET    /communications/availability/notification-settings
* PUT    /communications/availability/notification-settings

Phase 2.1 (ADR-012, 2026-05-09): the legacy planner-event surface
(``GET/POST/PATCH /communications/planner/events*``) was removed.
The canonical task / planner-row CRUD is ``/api/v1/activities`` (see
``backend/app/api/v1/activities_v1.py``); the FE shim in
``hostflow-frontend/src/api/communications.ts`` keeps the legacy
typed callers working until Phase 3 deletes the shim.

The working-hours / availability validation helpers
(``_assert_within_working_hours_or_overridden``,
``_tenant_enforces_planner_working_hours``) remain — Phase 3 will
hook them into ``PATCH /api/v1/activities/{id}`` for time-bound
activities (`Activity.starts_at IS NOT NULL`).
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
from backend.app.models.communication import CommunicationTimeOffRequest
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.timeoff_cleanup import (
    cancel_assignee_schedule_during_timeoff,
)
from backend.app.services.working_hours_window import (
    is_within_working_hours,
    schedule_applies,
)
from backend.app.services.notification_settings_v1 import normalize_notification_settings_v1

from .._helpers.access import (
    _get_tenant_or_404,
    _require_any_comm_feature,
    _require_comm_feature,
)
from .._helpers.dto import _timeoff_out
from .._helpers.utils import _as_dict, _now_utc
from .._helpers.working_hours import (
    _normalize_working_hours,
    _partial_day_blocks_now,
    _validate_iso_date_range,
)
from ..schemas import (
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


# Phase 2.1 (ADR-012, 2026-05-09): legacy planner-event HTTP routes
# (``GET /communications/planner/events``,
# ``GET /communications/planner/events/{id}``) have been removed.
# Listing / fetching is now served by ``GET /api/v1/activities`` /
# ``GET /api/v1/activities/{id}``; the FE shim in
# ``hostflow-frontend/src/api/communications.ts`` keeps the legacy
# typed callers working until Phase 3 deletes the shim.

# G-4 stage 3: tenant setting that enables server-side rejection of
# time-bound activities (formerly planner events) scheduled outside
# the assignee's working hours. Default OFF to preserve current
# behaviour. Path mirrors the reminder shift policy:
#   tenant.settings["planner"]["enforce_working_hours"]: bool
# The schema-level `allow_outside_hours=True` flag is the per-event
# override — operators consciously schedule the after-hours interview
# instead of being silently blocked. The flag is consumed by the
# /api/v1/activities create/patch handlers (Phase 3 wiring).
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


# Phase 2.1 (ADR-012, 2026-05-09): legacy planner-event create/patch
# routes (``POST /communications/planner/events``,
# ``PATCH /communications/planner/events/{id}``) have been removed.
# Canonical create / update is now ``POST /api/v1/activities`` /
# ``PATCH /api/v1/activities/{id}``; the FE shim in
# ``hostflow-frontend/src/api/communications.ts`` keeps the legacy
# typed callers (``createCommunicationPlannerEvent``,
# ``patchCommunicationPlannerEvent``) working until Phase 3 deletes
# the shim.
