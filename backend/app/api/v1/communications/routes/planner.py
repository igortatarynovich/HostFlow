"""Planner / availability / time-off endpoints for the communications API.

Endpoints (URL paths preserved as registered in the parent router):

* GET    /communications/time-off/requests
* POST   /communications/time-off/requests
* POST   /communications/time-off/requests/{id}/cancel
* POST   /communications/time-off/requests/{id}/decision
* GET    /communications/availability/working-hours
* PUT    /communications/availability/working-hours
* GET    /communications/planner/events
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
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.services.communications_access import assert_comm_feature_access

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
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    stmt = stmt.order_by(sa.asc(CommunicationPlannerEvent.start_at), sa.asc(CommunicationPlannerEvent.created_at)).limit(limit).offset(offset)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationPlannerEventListResponse(items=[_planner_event_out(r) for r in rows], total=total)


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
    row = CommunicationPlannerEvent(
        tenant_id=tenant_id,
        title=body.title.strip(),
        description=body.description,
        kind=(body.kind or "task").strip().lower(),
        status=(body.status or "planned").strip().lower(),
        priority=(body.priority or "normal").strip().lower(),
        start_at=body.start_at if body.start_at.tzinfo else body.start_at.replace(tzinfo=timezone.utc),
        end_at=(body.end_at if (body.end_at and body.end_at.tzinfo) else (body.end_at.replace(tzinfo=timezone.utc) if body.end_at else None)),
        all_day=bool(body.all_day),
        owner_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        assignee_id=body.assignee_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        linked_candidate_id=body.linked_candidate_id,
        linked_company_id=body.linked_company_id,
        source=(body.source or "manual").strip().lower(),
        payload=_as_dict(body.payload),
    )
    db.add(row)
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
    if "payload" in patch and patch["payload"] is not None:
        row.payload = _as_dict(patch["payload"])
    row.updated_at = _now_utc()
    await db.commit()
    await db.refresh(row)
    return _planner_event_out(row)
