from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import (
    CommunicationAllocationAudit,
    CommunicationThread,
    CommunicationTimeOffRequest,
)
from backend.app.models.tenant import Tenant


DAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass
class AllocationCandidate:
    manager_id: str
    queue_order: int
    priority_weight: int
    current_load_cfg: int
    dynamic_open_threads: int
    max_concurrent: int
    availability_state: str
    eligible: bool
    reasons: List[str]

    @property
    def effective_load(self) -> int:
        return max(0, int(self.current_load_cfg or 0)) + max(0, int(self.dynamic_open_threads or 0))

    @property
    def load_ratio(self) -> float:
        cap = max(1, int(self.max_concurrent or 1))
        return self.effective_load / cap


def _settings_root(tenant: Tenant) -> Dict[str, Any]:
    return tenant.settings if isinstance(tenant.settings, dict) else {}


def _communications_settings(tenant: Tenant) -> Dict[str, Any]:
    root = _settings_root(tenant)
    raw = root.get("communications")
    return raw if isinstance(raw, dict) else {}


def _manager_queue_settings(tenant: Tenant) -> Dict[str, Any]:
    raw = _communications_settings(tenant).get("managerQueue")
    return raw if isinstance(raw, dict) else {}


def _channels_settings(tenant: Tenant) -> Dict[str, Any]:
    raw = _communications_settings(tenant).get("channels")
    return raw if isinstance(raw, dict) else {}


def _parse_hm(value: str | None) -> Tuple[int, int] | None:
    if not value or not isinstance(value, str) or ":" not in value:
        return None
    try:
        hh, mm = value.split(":", 1)
        h = int(hh)
        m = int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except Exception:
        return None
    return None


def _is_in_schedule(now_local: datetime, schedule: Any) -> bool:
    if not isinstance(schedule, list) or not schedule:
        return True
    day_code = DAY_CODES[now_local.weekday()]
    for slot in schedule:
        if not isinstance(slot, dict):
            continue
        if str(slot.get("day", "")).lower() != day_code:
            continue
        if slot.get("enabled") is False:
            return False
        start = _parse_hm(slot.get("start"))
        end = _parse_hm(slot.get("end"))
        if not start or not end:
            return True
        cur_min = now_local.hour * 60 + now_local.minute
        start_min = start[0] * 60 + start[1]
        end_min = end[0] * 60 + end[1]
        return start_min <= cur_min <= end_min
    return False


def _time_off_blocks_now(now_local: datetime, item: Dict[str, Any]) -> tuple[bool, List[str]]:
    reasons: List[str] = ["approved_time_off"]
    partial_day = str(item.get("partial_day") or "").strip().lower()
    payload = item.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    time_window = payload.get("time_window")
    time_window = time_window if isinstance(time_window, dict) else {}
    start_date = str(item.get("start_date") or "").strip()
    end_date = str(item.get("end_date") or "").strip()
    today = now_local.date().isoformat()

    if partial_day and start_date == end_date == today:
        minutes = now_local.hour * 60 + now_local.minute
        from_hm = _parse_hm(time_window.get("from"))
        to_hm = _parse_hm(time_window.get("to"))
        if from_hm and to_hm:
            start_min = from_hm[0] * 60 + from_hm[1]
            end_min = to_hm[0] * 60 + to_hm[1]
            if start_min <= minutes <= end_min:
                reasons.append(f"time_off_partial:window:{time_window.get('from')}-{time_window.get('to')}")
                return True, reasons
            reasons.append("time_off_partial:not_in_effect")
            return False, reasons
        split_min = 13 * 60  # MVP split point; can be refined per schedule later
        if partial_day == "first_half":
            if minutes < split_min:
                reasons.append("time_off_partial:first_half")
                return True, reasons
            reasons.append("time_off_partial:not_in_effect")
            return False, reasons
        if partial_day == "second_half":
            if minutes >= split_min:
                reasons.append("time_off_partial:second_half")
                return True, reasons
            reasons.append("time_off_partial:not_in_effect")
            return False, reasons

    if partial_day:
        reasons.append(f"time_off_partial:{partial_day}")
    return True, reasons


def _now_for_tenant(tenant: Tenant, now_override: datetime | None = None) -> datetime:
    if now_override is not None:
        if now_override.tzinfo is None:
            return now_override.replace(tzinfo=timezone.utc)
        return now_override
    tz_name = str(_channels_settings(tenant).get("timezone") or "UTC").strip() or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz)


async def _open_thread_counts_by_assignee(db: AsyncSession, tenant_id: str) -> Dict[str, int]:
    stmt = (
        sa.select(CommunicationThread.assignee_id, sa.func.count())
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.assignee_id.isnot(None),
            CommunicationThread.is_archived.is_(False),
            CommunicationThread.status.in_(["open", "pending", "active"]),
        )
        .group_by(CommunicationThread.assignee_id)
    )
    rows = (await db.execute(stmt)).all()
    result: Dict[str, int] = {}
    for assignee_id, cnt in rows:
        if assignee_id:
            result[str(assignee_id)] = int(cnt or 0)
    return result


async def _approved_time_off_map_for_date(db: AsyncSession, *, tenant_id: str, date_iso: str) -> Dict[str, Dict[str, Any]]:
    stmt = (
        sa.select(
            CommunicationTimeOffRequest.requester_user_id,
            CommunicationTimeOffRequest.request_type,
            CommunicationTimeOffRequest.partial_day,
            CommunicationTimeOffRequest.start_date,
            CommunicationTimeOffRequest.end_date,
            CommunicationTimeOffRequest.payload,
            CommunicationTimeOffRequest.id,
        )
        .where(
            CommunicationTimeOffRequest.tenant_id == tenant_id,
            CommunicationTimeOffRequest.status == "approved",
            CommunicationTimeOffRequest.start_date <= date_iso,
            CommunicationTimeOffRequest.end_date >= date_iso,
        )
    )
    rows = (await db.execute(stmt)).all()
    result: Dict[str, Dict[str, Any]] = {}
    for requester_user_id, request_type, partial_day, start_date, end_date, payload, req_id in rows:
        if requester_user_id:
            result[str(requester_user_id)] = {
                "request_type": request_type,
                "partial_day": partial_day,
                "start_date": start_date,
                "end_date": end_date,
                "payload": payload if isinstance(payload, dict) else {},
                "request_id": req_id,
            }
    return result


def _max_concurrent_for_channel(item: Dict[str, Any], channel: str) -> int:
    availability = item.get("availability")
    availability = availability if isinstance(availability, dict) else {}
    # Future extension: call channels can use calls cap. For now treat all non-voice as chat.
    if channel in {"call", "phone"}:
        return max(1, int(availability.get("maxConcurrentCalls") or 1))
    return max(1, int(availability.get("maxConcurrentChats") or 10))


async def _evaluate_allocator(
    db: AsyncSession,
    *,
    tenant: Tenant,
    thread_channel: str,
    current_thread_id: str | None = None,
    now_override: datetime | None = None,
) -> Dict[str, Any]:
    queue = _manager_queue_settings(tenant)
    if not queue or queue.get("enabled") is False:
        return {"assigned": False, "reason": "queue_disabled", "strategy": queue.get("strategy") if isinstance(queue, dict) else None, "candidates": []}

    strategy = str(queue.get("strategy") or "manual")
    if strategy == "manual":
        return {"assigned": False, "reason": "manual_strategy", "strategy": strategy, "candidates": []}

    items = queue.get("items")
    if not isinstance(items, list) or not items:
        return {"assigned": False, "reason": "queue_empty", "strategy": strategy, "candidates": []}

    respect_schedules = bool(queue.get("respectSchedules", True))
    respect_availability = bool(queue.get("respectAvailability", True))
    now_local = _now_for_tenant(tenant, now_override=now_override)
    open_counts = await _open_thread_counts_by_assignee(db, str(tenant.id))
    date_iso = now_local.date().isoformat()
    approved_time_off = await _approved_time_off_map_for_date(db, tenant_id=str(tenant.id), date_iso=date_iso)
    if current_thread_id:
        # exclude current thread from dynamic load if already assigned (best-effort)
        stmt = sa.select(CommunicationThread.assignee_id).where(
            CommunicationThread.tenant_id == str(tenant.id),
            CommunicationThread.id == str(current_thread_id),
        )
        current_assignee = (await db.execute(stmt)).scalar_one_or_none()
        if current_assignee:
            key = str(current_assignee)
            open_counts[key] = max(0, int(open_counts.get(key, 0)) - 1)

    candidates: List[AllocationCandidate] = []
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        manager_id = str(raw.get("managerId") or "").strip()
        if not manager_id:
            continue
        reasons: List[str] = []
        eligible = True
        if raw.get("enabled") is False:
            eligible = False
            reasons.append("disabled")

        if eligible and isinstance(raw.get("channels"), list) and raw.get("channels"):
            channels = [str(c) for c in raw.get("channels") if c]
            if thread_channel not in channels:
                eligible = False
                reasons.append("channel_not_allowed")

        if eligible and respect_schedules and not _is_in_schedule(now_local, raw.get("schedule")):
            eligible = False
            reasons.append("outside_schedule")

        active_time_off = approved_time_off.get(manager_id)
        if eligible and active_time_off:
            blocks_now, timeoff_reasons = _time_off_blocks_now(now_local, active_time_off)
            if blocks_now:
                eligible = False
            reasons.extend(timeoff_reasons)

        availability = raw.get("availability")
        availability = availability if isinstance(availability, dict) else {}
        state = str(availability.get("state") or "available")
        if eligible and respect_availability and state not in {"available"}:
            eligible = False
            reasons.append(f"availability:{state}")

        current_load_cfg = int(availability.get("currentLoad") or 0)
        dynamic_open = int(open_counts.get(manager_id, 0))
        max_concurrent = _max_concurrent_for_channel(raw, thread_channel)
        if eligible and respect_availability and (current_load_cfg + dynamic_open) >= max_concurrent:
            eligible = False
            reasons.append("at_capacity")

        candidates.append(
            AllocationCandidate(
                manager_id=manager_id,
                queue_order=int(raw.get("queueOrder") or idx),
                priority_weight=max(1, int(raw.get("priorityWeight") or 100)),
                current_load_cfg=max(0, current_load_cfg),
                dynamic_open_threads=max(0, dynamic_open),
                max_concurrent=max_concurrent,
                availability_state=state,
                eligible=eligible,
                reasons=reasons,
            )
        )

    eligible_candidates = [c for c in candidates if c.eligible]
    winner: AllocationCandidate | None = None
    if eligible_candidates:
        if strategy == "least_busy":
            winner = min(eligible_candidates, key=lambda c: (c.load_ratio, c.effective_load, c.queue_order))
        elif strategy == "weighted_round_robin":
            winner = max(eligible_candidates, key=lambda c: ((c.priority_weight / max(1, c.effective_load + 1)), -c.queue_order))
        else:
            winner = min(eligible_candidates, key=lambda c: c.queue_order)

    return {
        "assigned": bool(winner),
        "reason": None if winner else "no_eligible_managers",
        "strategy": strategy,
        "winner_manager_id": winner.manager_id if winner else None,
        "candidates": [
            {
                "manager_id": c.manager_id,
                "eligible": c.eligible,
                "reasons": c.reasons,
                "effective_load": c.effective_load,
                "max_concurrent": c.max_concurrent,
                "queue_order": c.queue_order,
                "priority_weight": c.priority_weight,
                "availability_state": c.availability_state,
                "load_ratio": round(c.load_ratio, 4),
            }
            for c in sorted(candidates, key=lambda x: x.queue_order)
        ],
        "evaluated_at": now_local.isoformat(),
    }


async def _write_allocation_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    mode: str,
    channel: str,
    thread_id: str | None,
    actor_user_id: str | None,
    eval_result: Dict[str, Any],
    payload: Dict[str, Any] | None = None,
) -> None:
    evaluated_at = None
    raw_eval_at = eval_result.get("evaluated_at")
    if isinstance(raw_eval_at, str):
        try:
            evaluated_at = datetime.fromisoformat(raw_eval_at)
        except Exception:
            evaluated_at = None
    audit = CommunicationAllocationAudit(
        tenant_id=tenant_id,
        mode=mode,
        channel=channel,
        thread_id=thread_id,
        actor_user_id=actor_user_id,
        strategy=str(eval_result.get("strategy") or "") or None,
        assigned=bool(eval_result.get("assigned")),
        assignee_id=(str(eval_result.get("winner_manager_id") or "") or str(eval_result.get("assignee_id") or "") or None),
        reason=(str(eval_result.get("reason") or "") or None),
        evaluated_at=evaluated_at,
        candidates_json=(eval_result.get("candidates") if isinstance(eval_result.get("candidates"), list) else []),
        payload=payload or {},
    )
    db.add(audit)


async def preview_allocation(
    db: AsyncSession,
    *,
    tenant: Tenant,
    channel: str,
    now_override: datetime | None = None,
) -> Dict[str, Any]:
    result = await _evaluate_allocator(
        db,
        tenant=tenant,
        thread_channel=channel,
        now_override=now_override,
    )
    await _write_allocation_audit(
        db,
        tenant_id=str(tenant.id),
        mode="preview",
        channel=channel,
        thread_id=None,
        actor_user_id=None,
        eval_result=result,
        payload={"now_override": now_override.isoformat() if now_override else None},
    )
    await db.flush()
    return result


async def allocate_thread(
    db: AsyncSession,
    *,
    tenant: Tenant,
    thread: CommunicationThread,
    actor_user_id: str | None = None,
) -> Dict[str, Any]:
    eval_result = await _evaluate_allocator(
        db,
        tenant=tenant,
        thread_channel=thread.channel,
        current_thread_id=str(thread.id),
    )
    strategy = str(eval_result.get("strategy") or "manual")
    winner_id = eval_result.get("winner_manager_id")
    queue = _manager_queue_settings(tenant)
    items = queue.get("items") if isinstance(queue, dict) else None
    if not winner_id:
        await _write_allocation_audit(
            db,
            tenant_id=str(tenant.id),
            mode="allocate",
            channel=thread.channel,
            thread_id=str(thread.id),
            actor_user_id=actor_user_id,
            eval_result=eval_result,
            payload={"thread_status": thread.status},
        )
        return {
            "assigned": False,
            "reason": eval_result.get("reason") or "no_eligible_managers",
            "strategy": strategy,
            "candidates": eval_result.get("candidates") or [],
        }

    thread.assignee_id = str(winner_id)
    thread.queue_assigned_by = strategy
    thread.updated_at = datetime.now(timezone.utc)

    # Persist queue rotation for round-robin variants by moving winner to the end.
    if strategy in {"round_robin", "weighted_round_robin"} and isinstance(items, list):
        max_order = max((int((it or {}).get("queueOrder") or i) for i, it in enumerate(items) if isinstance(it, dict)), default=0)
        for i, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            if str(raw.get("managerId") or "").strip() == str(winner_id):
                raw["queueOrder"] = max_order + 1
                break
        # Normalize ordering to avoid unbounded growth
        sorted_items = sorted(
            [it for it in items if isinstance(it, dict)],
            key=lambda x: int(x.get("queueOrder") or 0),
        )
        for idx, raw in enumerate(sorted_items):
            raw["queueOrder"] = idx
        root = _settings_root(tenant)
        comm = _communications_settings(tenant) or {}
        queue_copy = dict(queue)
        queue_copy["items"] = sorted_items
        comm = dict(comm)
        comm["managerQueue"] = queue_copy
        root = dict(root)
        root["communications"] = comm
        tenant.settings = root

    await db.flush()
    await _write_allocation_audit(
        db,
        tenant_id=str(tenant.id),
        mode="allocate",
        channel=thread.channel,
        thread_id=str(thread.id),
        actor_user_id=actor_user_id,
        eval_result={
            **eval_result,
            "assigned": True,
            "assignee_id": str(winner_id),
            "winner_manager_id": str(winner_id),
            "reason": None,
            "strategy": strategy,
        },
        payload={"thread_status": thread.status, "queue_assigned_by": strategy},
    )
    return {
        "assigned": True,
        "thread_id": str(thread.id),
        "assignee_id": str(winner_id),
        "strategy": strategy,
        "actor_user_id": actor_user_id,
        "candidates": eval_result.get("candidates") or [],
    }
