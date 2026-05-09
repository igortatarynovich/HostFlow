"""Manager queue: unavailable assignee → fallback peer by queue + optional **weighted day load**.

When ``respectAvailability`` is on, we can pick the fallback using the same calendar
day as the event (``load_context['anchor']``): sum **non-equivalent** work items
(planner kinds + active reminders) with tunable weights, then choose the manager with
the lowest score (ties: earlier in ``managerQueue.items``).

Phase 2.1 (ADR-012, 2026-05-09): both halves of the load query now read from
the canonical ``activities`` table.

* Time-bound (planner-style) rows are ``Activity.starts_at IS NOT NULL``,
  scored on the ``[day_start, day_end)`` window matched against
  ``starts_at``. The original planner ``kind`` survives in
  ``Activity.metadata_['planner']['kind']`` (preserved by the
  ``communication_planner_events`` → ``activities`` backfill in Alembic
  ``202607150004_pti``); we fall back to ``Activity.type`` for natively
  created activities.
* Deadline-only (reminder-style) rows are ``Activity.starts_at IS NULL``,
  scored on the same window matched against ``due_at``. The reminder
  ``type`` is just ``Activity.type``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Phase 2.1 (ADR-012, 2026-05-09): import ``Activity`` via the
# ``backend.app.models.reminder`` alias (``Reminder is Activity``
# post-Phase-1.3) to avoid the duplicate-package-path footgun under
# Docker — see ``models/user_notification.py`` docstring + the matching
# comment in ``services/timeoff_cleanup.py``.
from backend.app.models.reminder import Reminder as Activity
from backend.app.models.tenant import Tenant
from backend.app.services.assignee_load_taxonomy import (
    LOAD_PRIORITY_MULT,
    PLANNER_STATUS_LOAD_MULT,
    REMINDER_STATUS_LOAD_MULT,
    planner_kind_base_load,
    reminder_type_base_load,
)
from backend.app.services.plan_feature_gates import (
    plan_allows_smart_operations_bundle,
    resolve_tenant_plan_code,
)

logger = logging.getLogger(__name__)

__all__ = [
    "merge_assignee_resolution",
    "pick_first_available_manager_excluding",
    "planner_event_load_weight",
    "reminder_load_weight",
    "resolve_assignee_id_with_queue_fallback",
    "smart_assignee_load_context",
]


def planner_event_load_weight(*, kind: str, priority: str, status: str) -> float:
    p = str(priority or "normal").strip().lower()
    s = str(status or "planned").strip().lower()
    base = planner_kind_base_load(kind)
    base *= float(LOAD_PRIORITY_MULT.get(p, 1.0))
    base *= float(PLANNER_STATUS_LOAD_MULT.get(s, 1.0))
    return max(0.0, base)


def reminder_load_weight(*, rtype: str, priority: str | None, status: str) -> float:
    p = str(priority or "normal").strip().lower()
    s = str(status or "").strip().lower()
    base = reminder_type_base_load(rtype)
    base *= float(LOAD_PRIORITY_MULT.get(p, 1.0))
    base *= float(REMINDER_STATUS_LOAD_MULT.get(s, 1.0))
    return max(0.0, base)


async def smart_assignee_load_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    anchor: datetime | None,
) -> dict[str, Any] | None:
    """
    ``load_context`` for **weighted** manager-queue fallback. Returns ``None`` on
    plans without the smart-operations bundle (queue order only; same API surface).
    """
    if anchor is None:
        return None
    plan = await resolve_tenant_plan_code(db, tenant_id)
    if not plan_allows_smart_operations_bundle(plan, tenant_id=tenant_id):
        return None
    return {"anchor": anchor}


def _normalize_team_state(value: Any) -> str:
    return str(value or "").strip().lower() or "available"


def _is_unavailable_team_state(state: str) -> bool:
    return state in {"offline", "busy", "break", "meeting"}


def _item_state_from_raw(raw: dict) -> str:
    av = raw.get("availability")
    if not isinstance(av, dict):
        return "available"
    return _normalize_team_state(av.get("state"))


def _parse_manager_queue(tenant: Tenant | None) -> tuple[bool, list[dict]]:
    if tenant is None or not isinstance(tenant.settings, dict):
        return (True, [])
    communications = tenant.settings.get("communications")
    if not isinstance(communications, dict):
        return (True, [])
    manager_queue = communications.get("managerQueue")
    if not isinstance(manager_queue, dict):
        return (True, [])
    respect = bool(manager_queue.get("respectAvailability", True))
    items = manager_queue.get("items")
    if not isinstance(items, list) or not items:
        return (respect, [])
    return (respect, [x for x in items if isinstance(x, dict)])


def _find_queue_item(items: list[dict], manager_id: str) -> dict | None:
    mid = str(manager_id or "").strip()
    if not mid:
        return None
    for raw in items:
        if str(raw.get("managerId") or "").strip() == mid:
            return raw
    return None


def _day_bounds_utc(anchor: datetime) -> tuple[datetime, datetime]:
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    a = anchor.astimezone(timezone.utc)
    day_start = a.replace(hour=0, minute=0, second=0, microsecond=0)
    return day_start, day_start + timedelta(days=1)


@dataclass
class _Avail:
    mid: str
    raw: dict
    queue_index: int


def _enumerate_available_managers(
    items: list[dict],
    *,
    exclude_id: str,
) -> list[_Avail]:
    ex = str(exclude_id or "").strip()
    out: list[_Avail] = []
    for i, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        mid = str(raw.get("managerId") or "").strip()
        if not mid or mid == ex:
            continue
        if raw.get("enabled") is False:
            continue
        st = _item_state_from_raw(raw)
        if _is_unavailable_team_state(st):
            continue
        out.append(_Avail(mid=mid, raw=raw, queue_index=i))
    return out


def pick_first_available_manager_excluding(
    items: list[dict],
    *,
    exclude_id: str,
) -> dict | None:
    """First enabled + available in queue order (no DB)."""
    avail = _enumerate_available_managers(items, exclude_id=exclude_id)
    if not avail:
        return None
    return avail[0].raw


async def compute_managers_weighted_day_load(
    db: AsyncSession,
    *,
    tenant_id: str,
    manager_ids: Sequence[str],
    day_start: datetime,
    day_end: datetime,
) -> dict[str, float]:
    """Sum planner + reminder weights for ``[day_start, day_end)`` (UTC-anchored day slice)."""
    ids = [str(x).strip() for x in manager_ids if str(x).strip()]
    if not ids:
        return {}
    loads: dict[str, float] = {i: 0.0 for i in ids}
    tid = str(tenant_id)

    # Time-bound (planner-style) activities — ``starts_at IS NOT NULL``.
    # Phase 2.1: ``kind`` lives in ``metadata.planner.kind`` for rows
    # backfilled from ``communication_planner_events``; natively created
    # activities just expose ``Activity.type``. We pull both and let the
    # Python side prefer the planner kind to keep weights identical to
    # pre-Phase-2.1 behaviour. ``metadata.planner.kind`` lookup is
    # transitional and removed in Phase 3 once UI/automation consistently
    # writes the planner taxonomy into ``Activity.type`` directly
    # (see todo ``p3-aliases-cleanup``).
    pl_rows = (
        await db.execute(
            select(
                Activity.assigned_to_user_id,
                Activity.type,
                Activity.priority,
                Activity.status,
                Activity.metadata_,
            ).where(
                Activity.tenant_id == tid,
                Activity.starts_at.is_not(None),
                Activity.assigned_to_user_id.isnot(None),
                Activity.assigned_to_user_id.in_(ids),
                Activity.starts_at >= day_start,
                Activity.starts_at < day_end,
            )
        )
    ).all()
    for aid, atype, pri, st, meta in pl_rows:
        if not aid:
            continue
        kind: str | None = None
        if isinstance(meta, dict):
            planner_meta = meta.get("planner")
            if isinstance(planner_meta, dict):
                raw_kind = planner_meta.get("kind")
                if isinstance(raw_kind, str) and raw_kind.strip():
                    kind = raw_kind.strip()
        if not kind:
            kind = str(atype or "task")
        key = str(aid)
        loads[key] = loads.get(key, 0.0) + planner_event_load_weight(
            kind=kind, priority=str(pri or "normal"), status=str(st or "planned")
        )

    # Deadline-only (reminder-style) activities — ``starts_at IS NULL``.
    r_rows = (
        await db.execute(
            select(
                Activity.assigned_to_user_id,
                Activity.type,
                Activity.priority,
                Activity.status,
            ).where(
                Activity.tenant_id == tid,
                Activity.starts_at.is_(None),
                Activity.assigned_to_user_id.isnot(None),
                Activity.assigned_to_user_id.in_(ids),
                Activity.due_at >= day_start,
                Activity.due_at < day_end,
            )
        )
    ).all()
    for aid, rtype, pri, st in r_rows:
        if not aid:
            continue
        key = str(aid)
        loads[key] = loads.get(key, 0.0) + reminder_load_weight(
            rtype=str(rtype or "custom"), priority=str(pri) if pri else None, status=str(st or "")
        )
    return loads


async def pick_best_available_manager_weighted(
    db: AsyncSession,
    *,
    tenant_id: str,
    items: list[dict],
    exclude_id: str,
    anchor: datetime,
) -> tuple[dict | None, dict[str, Any] | None]:
    """
    Choose among available managers: lowest **weighted day load**, tie → earlier in queue.
    Returns ``(raw_item, meta)`` where ``meta`` has candidate loads + window (for audit).
    """
    avail = _enumerate_available_managers(items, exclude_id=exclude_id)
    if not avail:
        return None, None
    if len(avail) == 1:
        m = avail[0]
        day_start, day_end = _day_bounds_utc(anchor)
        meta = {
            "resolution_method": "queue_order",
            "load_note": "single_alternative",
            "load_window_utc": {"start": day_start.isoformat(), "end": day_end.isoformat()},
            "per_manager_load": {m.mid: 0.0},
        }
        return m.raw, meta
    day_start, day_end = _day_bounds_utc(anchor)
    mids = [a.mid for a in avail]
    try:
        loads = await compute_managers_weighted_day_load(
            db, tenant_id=tenant_id, manager_ids=mids, day_start=day_start, day_end=day_end
        )
    except Exception:
        logger.exception("weighted assignee load query failed; falling back to queue order")
        m = min(avail, key=lambda x: x.queue_index)
        return m.raw, {
            "resolution_method": "queue_order",
            "load_error": "load_query_failed",
            "per_manager_load": {a.mid: 0.0 for a in avail},
        }
    # Sort by (load asc, queue_index asc)
    best = sorted(avail, key=lambda a: (float(loads.get(a.mid, 0.0)), a.queue_index))[0]
    score = float(loads.get(best.mid, 0.0))
    meta = {
        "resolution_method": "least_weighted_load",
        "load_window_utc": {"start": day_start.isoformat(), "end": day_end.isoformat()},
        "per_manager_load": {m: float(loads.get(m, 0.0)) for m in mids},
        "winner_load": score,
    }
    return best.raw, meta


def _build_audit(
    requested_id: str,
    chosen: dict,
    *,
    reason: str,
    requested_state: str | None = None,
    load_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if load_meta and isinstance(load_meta, dict):
        for k, v in load_meta.items():
            if v is not None:
                out[k] = v
    out["assignee_auto_reassigned"] = True
    out["requested_assignee_id"] = str(requested_id).strip()
    out["resolved_assignee_id"] = str(chosen.get("managerId") or "").strip()
    out["reason"] = reason
    if requested_state is not None and str(requested_state).strip():
        out["requested_team_state"] = str(requested_state).strip()
    return out


def merge_assignee_resolution(
    base: Any,
    resolution: dict[str, Any] | None,
) -> dict[str, Any]:
    p = dict(base) if isinstance(base, dict) else {}
    if resolution and isinstance(resolution, dict) and resolution.get("assignee_auto_reassigned"):
        p = {**p, "assignee_resolution": resolution}
    return p


async def resolve_assignee_id_with_queue_fallback(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: str | None,
    allow_unavailable_assignee: bool,
    load_context: dict[str, Any] | None = None,
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """
    Return ``(effective_assignee_id, audit)``.

    If ``load_context`` contains an ``anchor`` datetime, fallback assignee is chosen by
    **least weighted day load** among available queue members; otherwise by queue order.
    """
    if not assignee_id or allow_unavailable_assignee:
        return (str(assignee_id).strip() if assignee_id else None, None)

    requested = str(assignee_id).strip()
    tenant = await db.get(Tenant, str(tenant_id))
    respect, items = _parse_manager_queue(tenant)
    if not respect or not items:
        return (requested, None)

    match = _find_queue_item(items, requested)
    if match is None:
        return (requested, None)
    if match.get("enabled") is False:
        alt, lmeta = await _pick_alternative(
            db,
            tenant_id=tenant_id,
            items=items,
            exclude_id=requested,
            load_context=load_context,
        )
        if alt is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "assignee_unavailable",
                    "message": "assignee is disabled in manager queue and no other assignee is available",
                    "assignee_id": requested,
                    "hint": "Pass allow_unavailable_assignee=true to override.",
                },
            )
        return (
            str(alt.get("managerId") or "").strip(),
            _build_audit(requested, alt, reason="assignee_disabled_in_queue", load_meta=lmeta),
        )
    st = _item_state_from_raw(match)
    if not _is_unavailable_team_state(st):
        return (requested, None)
    alt, lmeta = await _pick_alternative(
        db,
        tenant_id=tenant_id,
        items=items,
        exclude_id=requested,
        load_context=load_context,
    )
    if alt is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "assignee_unavailable",
                "message": f"assignee team state is '{st}' and no other assignee is available in the queue",
                "assignee_id": requested,
                "state": st,
                "hint": "Pass allow_unavailable_assignee=true to override.",
            },
        )
    return (
        str(alt.get("managerId") or "").strip(),
        _build_audit(requested, alt, reason="assignee_unavailable_team_state", requested_state=st, load_meta=lmeta),
    )


async def _pick_alternative(
    db: AsyncSession,
    *,
    tenant_id: str,
    items: list[dict],
    exclude_id: str,
    load_context: dict[str, Any] | None,
) -> tuple[dict | None, dict[str, Any] | None]:
    anchor: datetime | None = None
    if load_context and isinstance(load_context, dict):
        raw = load_context.get("anchor")
        if isinstance(raw, datetime):
            anchor = raw
    if anchor is not None:
        try:
            chosen, lmeta = await pick_best_available_manager_weighted(
                db,
                tenant_id=tenant_id,
                items=items,
                exclude_id=exclude_id,
                anchor=anchor,
            )
            if chosen is not None:
                return chosen, lmeta
        except Exception:
            logger.exception("pick_best_available_manager_weighted failed; using queue order")
    first = pick_first_available_manager_excluding(items, exclude_id=exclude_id)
    if first is None:
        return None, None
    if anchor is not None:
        day_start, day_end = _day_bounds_utc(anchor)
        return first, {
            "resolution_method": "queue_order",
            "load_note": "fallback_queue_after_weighted_error",
            "load_window_utc": {"start": day_start.isoformat(), "end": day_end.isoformat()},
            "per_manager_load": {},
        }
    return first, {"resolution_method": "queue_order", "per_manager_load": {}}
