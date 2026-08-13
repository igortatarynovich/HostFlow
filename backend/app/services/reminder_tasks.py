from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.reminder_event import ReminderEvent
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.services.audit import log_activity
from backend.app.services.candidate_lifecycle import (
    exclude_completed_candidate_entities_clause,
)
from backend.app.services.lead_lifecycle import (
    exclude_completed_lead_entities_clause,
)
from backend.app.services.team_assignee_auto import (
    merge_assignee_resolution,
    resolve_assignee_id_with_queue_fallback,
    smart_assignee_load_context,
)
from backend.app.services.user_notifications import (
    create_notification,
    mark_reminder_bell_notifications_read,
)
from backend.app.services.working_hours_window import (
    next_working_window_after,
    schedule_applies,
)

DEFAULT_REMIND_OFFSET_MINUTES = 15
ALLOWED_CHANNELS = {"internal"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_candidate_display_name(
    first_name: Optional[str],
    last_name: Optional[str],
    email: Optional[str],
) -> str:
    parts = [str(first_name or "").strip(), str(last_name or "").strip()]
    name = " ".join(p for p in parts if p).strip()
    if name:
        return name
    em = str(email or "").strip()
    return em


async def build_reminder_payload_enrichments_for_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminders: Sequence[Reminder],
) -> Dict[str, Dict[str, Any]]:
    """Non-persistent payload fields for API consumers (e.g. ``candidate_name`` for tasks UI)."""
    if not reminders:
        return {}
    from backend.app.models.candidate import Candidate

    candidate_ids: set[str] = set()
    for r in reminders:
        if str(r.entity_type or "").strip().lower() != "candidate":
            continue
        eid = str(r.entity_id or "").strip()
        if not eid:
            continue
        pl = r.payload if isinstance(r.payload, dict) else {}
        if str(pl.get("candidate_name") or "").strip() and str(pl.get("workforce_employee_id") or "").strip():
            continue
        candidate_ids.add(eid)
    if not candidate_ids:
        return {}

    from backend.app.models.workforce_employee import WorkforceEmployee

    rows = await db.execute(
        select(Candidate.id, Candidate.first_name, Candidate.last_name, Candidate.email).where(
            Candidate.tenant_id == tenant_id,
            Candidate.id.in_(list(candidate_ids)),
        )
    )
    name_by_id: Dict[str, str] = {}
    for cid, fn, ln, em in rows.all():
        label = _format_candidate_display_name(fn, ln, em)
        if label:
            name_by_id[str(cid)] = label

    emp_rows = await db.execute(
        select(WorkforceEmployee.candidate_id, WorkforceEmployee.id).where(
            WorkforceEmployee.tenant_id == tenant_id,
            WorkforceEmployee.candidate_id.in_(list(candidate_ids)),
        )
    )
    employee_by_candidate: Dict[str, str] = {}
    for cid, eid in emp_rows.all():
        if cid and eid:
            employee_by_candidate[str(cid)] = str(eid)

    out: Dict[str, Dict[str, Any]] = {}
    for r in reminders:
        if str(r.entity_type or "").strip().lower() != "candidate":
            continue
        eid = str(r.entity_id or "").strip()
        if not eid:
            continue
        pl = r.payload if isinstance(r.payload, dict) else {}
        merge: Dict[str, Any] = {}
        if not str(pl.get("candidate_name") or "").strip():
            nm = name_by_id.get(eid)
            if nm:
                merge["candidate_name"] = nm
        if not str(pl.get("workforce_employee_id") or "").strip():
            wf = employee_by_candidate.get(eid)
            if wf:
                merge["workforce_employee_id"] = wf
        if merge:
            out[str(r.id)] = merge
    return out


def _is_admin(role: Optional[str]) -> bool:
    if not role:
        return False
    from backend.app.auth.trust_roles import TrustRole, is_team_lead_org_actor, normalize_trust_role

    trust = normalize_trust_role(role)
    if trust in {TrustRole.administrator.value, TrustRole.superadmin.value}:
        return True
    return is_team_lead_org_actor(role)


def _assert_acl(reminder: Reminder, actor_id: str, role: Optional[str]) -> None:
    if _is_admin(role):
        return
    if actor_id not in {reminder.owner_id, reminder.assignee_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _log_event(
    db: AsyncSession,
    *,
    reminder_id: str,
    tenant_id: str,
    event_type: str,
    payload: Optional[dict] = None,
) -> ReminderEvent:
    event = ReminderEvent(
        reminder_id=reminder_id,
        tenant_id=tenant_id,
        event_type=event_type,
        payload=payload or {},
    )
    db.add(event)
    return event


async def _log_invoice_reminder_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder: Reminder,
    actor_id: Optional[str],
    action: str,
    payload: Optional[dict] = None,
) -> None:
    if reminder.entity_type != "invoice" or not reminder.entity_id:
        return
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        target_type="invoice",
        target_id=reminder.entity_id,
        payload={
            "invoice_id": reminder.entity_id,
            "reminder_id": reminder.id,
            "title": reminder.title,
            "status": reminder.status,
            **(payload or {}),
        },
    )


def _normalize_remind_at(
    due_at: datetime, remind_at: Optional[datetime], default_offset_minutes: int
) -> datetime:
    if remind_at is None:
        remind_at = due_at - timedelta(minutes=default_offset_minutes)
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)
    now = _now()
    if remind_at < now:
        return now
    return remind_at


# G-4 stage 2: tenant setting that opts a workspace into "shift reminders
# to assignee's next working window" behaviour. Default is OFF — turning
# it on changes when reminders fire and we don't want to silently retime
# existing tenants' workflows. Path:
#   tenant.settings["reminders"]["shift_due_at_outside_hours"]: bool
# When ON: if the assignee has a `working_hours_v1` schedule and the
# requested due_at falls outside, due_at is moved to the next opening
# and remind_at is shifted by the same delta (preserving the lead-time).
# When OFF (default): create_reminder behaves as before.
_REMINDER_SHIFT_SETTINGS_PATH = ("reminders", "shift_due_at_outside_hours")


def _tenant_shifts_reminders(tenant: Optional[Tenant]) -> bool:
    if tenant is None:
        return False
    settings = tenant.settings if isinstance(tenant.settings, dict) else None
    if not settings:
        return False
    cursor: Any = settings
    for key in _REMINDER_SHIFT_SETTINGS_PATH:
        if not isinstance(cursor, dict):
            return False
        cursor = cursor.get(key)
    return bool(cursor)


async def _maybe_shift_due_at_to_working_hours(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: Optional[str],
    due_at: datetime,
    remind_at: Optional[datetime],
) -> Tuple[datetime, Optional[datetime], Optional[Dict[str, Any]]]:
    """Apply the G-4 working-hours shift policy.

    Returns the (possibly shifted) `due_at`, `remind_at`, and a
    diagnostic dict suitable for stashing in `Reminder.payload` under
    `_working_hours_shift` (None if no shift was applied — keeps the
    payload clean for the common case).

    `remind_at` shift policy: preserve the original lead-time relative
    to due_at. If the caller passed a custom remind_at, the same delta
    is reapplied after the due_at shift. If they didn't pass one, the
    later `_normalize_remind_at` call computes the default offset
    against the new due_at. We return remind_at unchanged here when it
    is None, deferring to that downstream normaliser.
    """
    if not assignee_id:
        return due_at, remind_at, None
    tenant = await db.get(Tenant, str(tenant_id))
    if not _tenant_shifts_reminders(tenant):
        return due_at, remind_at, None
    user = await db.get(User, str(assignee_id))
    if user is None:
        return due_at, remind_at, None
    extra = user.extra if isinstance(user.extra, dict) else {}
    if not schedule_applies(extra):
        # No working-hours schedule configured for this assignee → skip
        # silently (callers shouldn't see different behaviour just
        # because the assignee never set their hours).
        return due_at, remind_at, None
    shifted_due = next_working_window_after(extra, due_at)
    if shifted_due == due_at:
        return due_at, remind_at, None
    # Shift remind_at by the same delta so the lead-time is preserved.
    # If remind_at is None, leave it for `_normalize_remind_at` to
    # default — using `shifted_due - DEFAULT_REMIND_OFFSET_MINUTES`
    # there is the right behaviour.
    delta = shifted_due - due_at
    shifted_remind: Optional[datetime] = remind_at + delta if remind_at is not None else None
    diag = {
        "original_due_at": due_at.isoformat(),
        "shifted_due_at": shifted_due.isoformat(),
        "delta_seconds": int(delta.total_seconds()),
        "reason": "outside_assignee_working_hours",
    }
    return shifted_due, shifted_remind, diag


def resolve_assignee_for_reminder_list(
    *,
    explicit_assignee_id: Optional[str],
    assignee_scope: str,
    viewer_id: str,
    viewer_role: Optional[str],
    preset_id: Optional[str] = None,
) -> Optional[str]:
    """Filter reminders by assignee, or None = whole team (admin / team_lead / HR)."""
    from backend.app.auth.trust_roles import can_use_team_assignee_scope

    if explicit_assignee_id and str(explicit_assignee_id).strip():
        return str(explicit_assignee_id).strip()
    scope = str(assignee_scope or "mine").strip().lower()
    if scope == "team" and can_use_team_assignee_scope(viewer_role, preset_id):
        return None
    return str(viewer_id).strip()


async def create_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str,
    payload: Dict[str, Any],
) -> Reminder:
    due_at_raw = payload.get("due_at")
    if not isinstance(due_at_raw, datetime):
        raise HTTPException(status_code=400, detail="due_at is required")
    due_at = due_at_raw if due_at_raw.tzinfo else due_at_raw.replace(tzinfo=timezone.utc)

    channel = payload.get("channel") or "internal"
    if channel not in ALLOWED_CHANNELS:
        raise HTTPException(status_code=400, detail="Unsupported channel")

    remind_at = payload.get("remind_at")
    if remind_at is not None and not isinstance(remind_at, datetime):
        raise HTTPException(status_code=400, detail="remind_at must be datetime or null")

    assignee_id = payload.get("assignee_id") or actor_id
    allow_unavailable_assignee = bool(payload.get("allow_unavailable_assignee", False))
    eff_assignee, assignee_resolution = await resolve_assignee_id_with_queue_fallback(
        db,
        tenant_id=tenant_id,
        assignee_id=str(assignee_id) if assignee_id else None,
        allow_unavailable_assignee=allow_unavailable_assignee,
        load_context=await smart_assignee_load_context(
            db, tenant_id=tenant_id, anchor=due_at
        ),
    )
    if eff_assignee:
        assignee_id = eff_assignee
    duration_minutes = payload.get("duration_minutes")
    if duration_minutes is not None:
        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="duration_minutes must be int or null")
        if duration_minutes <= 0:
            duration_minutes = None
    source = payload.get("source")
    if source is not None:
        source = str(source).strip() or None

    # G-4 stage 2: opt-in shift to assignee's working-hours window.
    # Default OFF — see `_tenant_shifts_reminders`. When applied, both
    # due_at and (if provided) remind_at move by the same delta. The
    # original due_at is preserved in payload._working_hours_shift for
    # explainability popovers (G-10) so operators can see "this was
    # auto-shifted from 03:00 → 09:00" instead of being confused.
    due_at, remind_at, shift_diag = await _maybe_shift_due_at_to_working_hours(
        db,
        tenant_id=tenant_id,
        assignee_id=assignee_id,
        due_at=due_at,
        remind_at=remind_at,
    )
    payload_blob: Dict[str, Any] = dict(payload.get("payload") or {})
    if shift_diag is not None:
        payload_blob["_working_hours_shift"] = shift_diag
    if assignee_resolution:
        payload_blob = merge_assignee_resolution(payload_blob, assignee_resolution)

    reminder = Reminder(
        tenant_id=tenant_id,
        type=payload.get("type") or "custom",
        entity_type=payload.get("entity_type") or "custom",
        entity_id=payload.get("entity_id") or "",
        title=payload.get("title") or payload.get("message"),
        description=payload.get("description"),
        owner_id=actor_id,
        assignee_id=assignee_id,
        priority=payload.get("priority") or "normal",
        channel=channel,
        due_at=due_at,
        remind_at=_normalize_remind_at(due_at, remind_at, DEFAULT_REMIND_OFFSET_MINUTES),
        duration_minutes=duration_minutes,
        source=source,
        snoozed_until=None,
        completed_at=None,
        recurrence_json=payload.get("recurrence_json"),
        status=ReminderStatus.pending,
        message=payload.get("message"),
        payload=payload_blob,
        created_by=actor_id,
    )
    db.add(reminder)
    await db.flush()
    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="created",
        payload={"actor_id": actor_id},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="automation.reminder_created",
        target_type=reminder.entity_type,
        target_id=reminder.entity_id,
        payload={
            "reminder_id": reminder.id,
            "type": reminder.type,
            "status": reminder.status,
            "due_at": reminder.due_at.isoformat() if reminder.due_at else None,
            "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
        },
    )
    await _log_invoice_reminder_activity(
        db,
        tenant_id=tenant_id,
        reminder=reminder,
        actor_id=actor_id,
        action="invoice.reminder_created",
        payload={"due_at": reminder.due_at.isoformat(), "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None},
    )
    return reminder


async def list_reminders(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: Optional[str] = None,
    entity: Optional[Tuple[str, str]] = None,
    entity_type_filter: Optional[str] = None,
    status_in: Optional[Sequence[str]] = None,
    type_in: Optional[Sequence[str]] = None,
    due_range: Optional[Tuple[datetime, datetime]] = None,
    q: Optional[str] = None,
    limit: Optional[int] = None,
    include_completed_entities: bool = False,
) -> List[Reminder]:
    stmt = select(Reminder).where(Reminder.tenant_id == tenant_id)
    if assignee_id:
        stmt = stmt.where(Reminder.assignee_id == assignee_id)
    if entity:
        entity_type, entity_id = entity
        stmt = stmt.where(
            Reminder.entity_type == entity_type,
            Reminder.entity_id == entity_id,
        )
    elif entity_type_filter:
        stmt = stmt.where(Reminder.entity_type == entity_type_filter)
    if status_in:
        stmt = stmt.where(Reminder.status.in_(list(status_in)))
    if type_in:
        stmt = stmt.where(Reminder.type.in_(list(type_in)))
    if due_range:
        start, end = due_range
        if start:
            stmt = stmt.where(Reminder.due_at >= start)
        if end:
            stmt = stmt.where(Reminder.due_at <= end)
    q_norm = (q or "").strip()
    if q_norm:
        like = f"%{q_norm}%"
        stmt = stmt.where(
            or_(
                func.coalesce(Reminder.title, "").ilike(like),
                func.coalesce(Reminder.description, "").ilike(like),
                func.coalesce(Reminder.message, "").ilike(like),
            )
        )
    # G-2: by default hide reminders attached to silenced candidates (rejected/declined/employed/
    # probation_ok/deleted). When the caller explicitly drills into a single entity (the entity
    # filter is set) we keep all rows so opening the candidate card still shows full history.
    if not include_completed_entities and entity is None:
        stmt = stmt.where(
            and_(
                exclude_completed_candidate_entities_clause(
                    tenant_id,
                    entity_type_col=Reminder.entity_type,
                    entity_id_col=Reminder.entity_id,
                ),
                exclude_completed_lead_entities_clause(
                    tenant_id,
                    entity_type_col=Reminder.entity_type,
                    entity_id_col=Reminder.entity_id,
                ),
            )
        )
    stmt = stmt.order_by(Reminder.due_at.asc())
    if limit is not None and limit > 0:
        stmt = stmt.limit(limit)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def _get_reminder(db: AsyncSession, tenant_id: str, reminder_id: str) -> Reminder:
    row = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.tenant_id == tenant_id,
        )
    )
    reminder = row.scalar_one_or_none()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


async def get_reminder_for_actor(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder_id: str,
    actor_id: str,
    role: Optional[str],
) -> Reminder:
    """Single-reminder fetch with the same ACL as PATCH (G-6 calendar focus-by-id)."""
    reminder = await _get_reminder(db, tenant_id, reminder_id)
    _assert_acl(reminder, actor_id, role)
    return reminder


async def refresh_open_typed_reminder_due(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    reminder_type: str,
    new_due_at: datetime,
    new_title: Optional[str] = None,
    payload_merge: Optional[Dict[str, Any]] = None,
) -> bool:
    """Automation-only: move due_at forward for one open reminder (no user ACL). Used for UOS inbound / client pipeline."""
    active = (
        ReminderStatus.pending,
        ReminderStatus.new,
        ReminderStatus.sent,
        ReminderStatus.overdue,
    )
    stmt = (
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == entity_type,
            Reminder.entity_id == entity_id,
            Reminder.type == reminder_type,
            Reminder.status.in_(list(active)),
        )
        .order_by(Reminder.created_at.asc())
        .limit(1)
    )
    r = (await db.execute(stmt)).scalars().first()
    if r is None:
        return False
    nd = new_due_at if new_due_at.tzinfo else new_due_at.replace(tzinfo=timezone.utc)
    r.due_at = nd
    r.remind_at = _normalize_remind_at(r.due_at, None, DEFAULT_REMIND_OFFSET_MINUTES)
    if new_title is not None:
        r.title = new_title
    if payload_merge:
        base = dict(r.payload) if isinstance(r.payload, dict) else {}
        base.update(payload_merge)
        r.payload = base
    if r.status == ReminderStatus.overdue:
        r.status = ReminderStatus.pending
    await db.flush()
    _log_event(
        db,
        reminder_id=r.id,
        tenant_id=tenant_id,
        event_type="due_refreshed",
        payload={"reason": "uos_inbound_followup", "due_at": nd.isoformat()},
    )
    return True


async def update_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder_id: str,
    actor_id: str,
    role: Optional[str],
    payload: Dict[str, Any],
) -> Reminder:
    reminder = await _get_reminder(db, tenant_id, reminder_id)
    _assert_acl(reminder, actor_id, role)

    for key in ("title", "description", "priority", "channel", "message", "source"):
        if key in payload and payload[key] is not None:
            setattr(reminder, key, payload[key])

    if "duration_minutes" in payload:
        duration_minutes = payload["duration_minutes"]
        if duration_minutes is None:
            reminder.duration_minutes = None
        else:
            try:
                duration_minutes_int = int(duration_minutes)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="duration_minutes must be int or null")
            reminder.duration_minutes = duration_minutes_int if duration_minutes_int > 0 else None

    if "assignee_id" in payload and payload["assignee_id"]:
        reminder.assignee_id = payload["assignee_id"]

    if "due_at" in payload and isinstance(payload["due_at"], datetime):
        due_at = payload["due_at"]
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        reminder.due_at = due_at

    # --- Phase 2.1 (ADR-012) transitional fields ---
    # The FE shim in `hostflow-frontend/src/api/communications.ts` maps
    # legacy planner-event PATCHes onto `PATCH /activities/{id}` and may
    # send any of `status`, `type`, `entity_type`, `entity_id`, `payload`.
    # Phase 3 cleanup MUST remove this whole block (and especially the
    # wholesale `payload` replace) — see the matching schema note in
    # `backend/app/api/v1/reminders_v2.py::ReminderUpdateRequest` and the
    # rationale in `docs/specs/architecture/phase-2-1-planner-tasks-into-activities.md`
    # §"Transitional backend addition".
    if "status" in payload and payload["status"] is not None:
        next_status = str(payload["status"]).strip().lower()
        # Closed Activity enum (ADR-012 §6) plus the transient legacy
        # planner statuses the shim still relays verbatim. Anything else
        # is a contract violation.
        allowed = {
            "planned",
            "in_progress",
            "done",
            "cancelled",
            "overdue",
            # Legacy planner / reminder statuses — collapsed to "planned"
            # by `activity_layer_v1` on read; we still accept them on
            # write so the shim doesn't have to translate per-call.
            "new",
            "pending",
            "sent",
        }
        if next_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "invalid_status",
                    "message": f"unknown reminder/activity status '{next_status}'",
                    "allowed": sorted(allowed),
                },
            )
        reminder.status = next_status

    if "type" in payload and payload["type"] is not None:
        new_type = str(payload["type"]).strip()
        if new_type:
            reminder.type = new_type

    if "entity_type" in payload and payload["entity_type"] is not None:
        new_entity_type = str(payload["entity_type"]).strip()
        if new_entity_type:
            reminder.entity_type = new_entity_type
    if "entity_id" in payload and payload["entity_id"] is not None:
        new_entity_id = str(payload["entity_id"]).strip()
        if new_entity_id:
            reminder.entity_id = new_entity_id

    if "payload" in payload and payload["payload"] is not None:
        # Wholesale replace — mirrors legacy planner PATCH semantics. The
        # canonical Activity update model merges payload; this branch is
        # transitional. Phase 3 must delete it and route any legitimate
        # "replace blob" need through a dedicated endpoint
        # (`PUT /activities/{id}/payload`).
        new_payload = payload["payload"]
        if not isinstance(new_payload, dict):
            raise HTTPException(
                status_code=400,
                detail="payload must be an object",
            )
        reminder.payload = dict(new_payload)

    if "remind_at" in payload:
        remind_at = payload["remind_at"]
        if remind_at is None:
            reminder.remind_at = _normalize_remind_at(
                reminder.due_at, None, DEFAULT_REMIND_OFFSET_MINUTES
            )
        elif isinstance(remind_at, datetime):
            reminder.remind_at = _normalize_remind_at(
                reminder.due_at, remind_at, DEFAULT_REMIND_OFFSET_MINUTES
            )
        else:
            raise HTTPException(status_code=400, detail="remind_at must be datetime or null")

    if "assignee_id" in payload or "due_at" in payload:
        eff_id, assignee_resolution = await resolve_assignee_id_with_queue_fallback(
            db,
            tenant_id=tenant_id,
            assignee_id=str(reminder.assignee_id) if reminder.assignee_id else None,
            allow_unavailable_assignee=bool(payload.get("allow_unavailable_assignee", False)),
            load_context=await smart_assignee_load_context(
                db, tenant_id=tenant_id, anchor=reminder.due_at
            ),
        )
        if eff_id is not None:
            reminder.assignee_id = eff_id
        if assignee_resolution:
            pb = dict(reminder.payload or {}) if isinstance(reminder.payload, dict) else {}
            reminder.payload = merge_assignee_resolution(pb, assignee_resolution)

    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="updated",
        payload={"actor_id": actor_id},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="automation.reminder_updated",
        target_type=reminder.entity_type,
        target_id=reminder.entity_id,
        payload={"reminder_id": reminder.id},
    )
    return reminder


async def snooze_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder_id: str,
    actor_id: str,
    role: Optional[str],
    minutes: Optional[int] = None,
    new_remind_at: Optional[datetime] = None,
) -> Reminder:
    reminder = await _get_reminder(db, tenant_id, reminder_id)
    _assert_acl(reminder, actor_id, role)
    if minutes is None and new_remind_at is None:
        raise HTTPException(status_code=400, detail="minutes or new_remind_at required")
    if minutes is not None:
        new_remind_at = _now() + timedelta(minutes=int(minutes))
    elif new_remind_at and new_remind_at.tzinfo is None:
        new_remind_at = new_remind_at.replace(tzinfo=timezone.utc)
    reminder.remind_at = _normalize_remind_at(reminder.due_at, new_remind_at, DEFAULT_REMIND_OFFSET_MINUTES)
    reminder.snoozed_until = reminder.remind_at
    reminder.status = ReminderStatus.pending
    reminder.sent_at = None
    # G-9: silence current bell rows so the snooze immediately quiets the user's bell.
    await mark_reminder_bell_notifications_read(
        db,
        tenant_id=tenant_id,
        reminder=reminder,
        reason="reminder_snoozed",
    )
    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="snoozed",
        payload={"actor_id": actor_id, "remind_at": reminder.remind_at.isoformat()},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="automation.reminder_snoozed",
        target_type=reminder.entity_type,
        target_id=reminder.entity_id,
        payload={"reminder_id": reminder.id, "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None},
    )
    return reminder


async def _spawn_next_recurrence(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str,
    reminder: Reminder,
) -> Optional[Reminder]:
    rec = reminder.recurrence_json or {}
    if not isinstance(rec, dict) or not rec:
        return None

    freq = (rec.get("freq") or "").lower()
    interval = int(rec.get("interval") or 1)
    if interval <= 0:
        interval = 1

    if freq == "daily":
        delta = timedelta(days=interval)
    elif freq == "weekly":
        delta = timedelta(weeks=interval)
    else:
        # simple custom: treat interval as days
        delta = timedelta(days=interval)

    next_due = reminder.due_at + delta
    next_remind = _normalize_remind_at(next_due, None, DEFAULT_REMIND_OFFSET_MINUTES)
    clone = Reminder(
        tenant_id=tenant_id,
        type=reminder.type,
        entity_type=reminder.entity_type,
        entity_id=reminder.entity_id,
        title=reminder.title,
        description=reminder.description,
        owner_id=reminder.owner_id,
        assignee_id=reminder.assignee_id,
        priority=reminder.priority,
        channel=reminder.channel,
        due_at=next_due,
        remind_at=next_remind,
        duration_minutes=reminder.duration_minutes,
        source=reminder.source,
        recurrence_json=reminder.recurrence_json,
        status=ReminderStatus.pending,
        message=reminder.message,
        payload=reminder.payload,
        created_by=actor_id,
    )
    db.add(clone)
    _log_event(
        db,
        reminder_id=clone.id,
        tenant_id=tenant_id,
        event_type="created",
        payload={"actor_id": actor_id, "source": reminder.id, "reason": "recurrence"},
    )
    return clone


async def complete_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder_id: str,
    actor_id: str,
    role: Optional[str],
    completed_at: Optional[datetime] = None,
) -> Reminder:
    reminder = await _get_reminder(db, tenant_id, reminder_id)
    _assert_acl(reminder, actor_id, role)
    ts = completed_at or _now()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    reminder.completed_at = ts
    reminder.status = ReminderStatus.done
    # G-9: completing the task in /app/tasks must immediately clear the bell.
    await mark_reminder_bell_notifications_read(
        db,
        tenant_id=tenant_id,
        reminder=reminder,
        reason="reminder_completed",
    )
    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="completed",
        payload={"actor_id": actor_id, "completed_at": ts.isoformat()},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="automation.reminder_completed",
        target_type=reminder.entity_type,
        target_id=reminder.entity_id,
        payload={"reminder_id": reminder.id, "completed_at": ts.isoformat()},
    )
    await _log_invoice_reminder_activity(
        db,
        tenant_id=tenant_id,
        reminder=reminder,
        actor_id=actor_id,
        action="invoice.reminder_completed",
        payload={"completed_at": ts.isoformat()},
    )
    await _spawn_next_recurrence(db, tenant_id=tenant_id, actor_id=actor_id, reminder=reminder)
    return reminder


async def mark_overdue_reminders(db: AsyncSession, *, tenant_id: str) -> int:
    now = _now()
    stmt = (
        update(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.status.in_([ReminderStatus.pending, ReminderStatus.new]),
            Reminder.due_at < now,
        )
        .values(status=ReminderStatus.overdue)
    )
    result = await db.execute(stmt)
    return result.rowcount or 0


async def deliver_due_reminders(db: AsyncSession, *, tenant_id: str) -> int:
    now = _now()
    rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.status.in_([ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue]),
            Reminder.remind_at.isnot(None),
            Reminder.remind_at <= now,
            Reminder.channel == "internal",
            Reminder.sent_at.is_(None),
        )
    )
    reminders = list(rows.scalars().all())
    delivered = 0
    for reminder in reminders:
        target_user = reminder.assignee_id or reminder.owner_id
        if not target_user:
            continue
        event_type = "reminder_overdue" if reminder.status == ReminderStatus.overdue else "reminder_due"
        payload = {
            "title": reminder.title,
            "description": reminder.description,
            "type": event_type,
            "reminder_id": str(reminder.id),
            "entity_type": reminder.entity_type,
            "entity_id": reminder.entity_id,
            "due_at": reminder.due_at.isoformat() if reminder.due_at else None,
            "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
            "priority": reminder.priority,
            "status": reminder.status,
            "severity": "high" if reminder.status == ReminderStatus.overdue else "medium",
            "requires_action": True,
            "source": "reminders",
            "dedupe_key": f"reminder:{event_type}:{reminder.id}:{str(target_user)}",
        }
        await create_notification(
            db,
            tenant_id=tenant_id,
            user_id=str(target_user),
            event_type=event_type,
            entity_type=reminder.entity_type,
            entity_id=reminder.entity_id,
            payload=payload,
            channel="in_app",
            delivered_at=now,
            dedupe_window_minutes=240,
        )
        _log_event(
            db,
            reminder_id=reminder.id,
            tenant_id=tenant_id,
            event_type="sent",
            payload={"to": target_user, "event_type": event_type},
        )
        reminder.sent_at = now
        if reminder.status in {ReminderStatus.new, ReminderStatus.pending}:
            reminder.status = ReminderStatus.sent
        delivered += 1
    return delivered
