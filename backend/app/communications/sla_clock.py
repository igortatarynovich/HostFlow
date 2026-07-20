"""C1.2 — SLA clock projection from events (breached is always derived)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import CommunicationThread
from backend.app.models.communication_thread_sla_event import (
    SLA_EVENT_PAUSE,
    SLA_EVENT_RESOLVE,
    SLA_EVENT_RESUME,
    SLA_EVENT_START,
    CommunicationThreadSlaEvent,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


@dataclass(slots=True)
class SlaClockProjection:
    started_at: str | None
    target_due_at: str | None
    resolved_at: str | None
    paused: bool
    paused_intervals: list[dict[str, str | None]]
    breached: bool
    status: str  # none | running | paused | resolved | breached

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "target_due_at": self.target_due_at,
            "resolved_at": self.resolved_at,
            "paused": self.paused,
            "paused_intervals": self.paused_intervals,
            "breached": self.breached,
            "status": self.status,
        }


def project_sla_clock(
    events: list[CommunicationThreadSlaEvent],
    *,
    now: datetime | None = None,
    fallback_due_at: datetime | None = None,
) -> SlaClockProjection:
    """Derive SLA state from ordered events. Never reads a stored breached flag."""
    now = now or _now()
    started_at: datetime | None = None
    target_due: datetime | None = None
    resolved_at: datetime | None = None
    paused = False
    pause_open: datetime | None = None
    intervals: list[dict[str, str | None]] = []

    ordered = sorted(events, key=lambda e: (e.at, e.created_at or e.at))
    for ev in ordered:
        et = str(ev.event_type or "").strip().lower()
        payload = dict(ev.payload or {})
        if et == SLA_EVENT_START:
            started_at = ev.at
            target_due = _parse_iso(payload.get("target_due_at")) or target_due
            resolved_at = None
            paused = False
            pause_open = None
        elif et == SLA_EVENT_PAUSE:
            if not paused:
                paused = True
                pause_open = ev.at
        elif et == SLA_EVENT_RESUME:
            if paused and pause_open is not None:
                intervals.append(
                    {
                        "paused_at": pause_open.isoformat(),
                        "resumed_at": ev.at.isoformat(),
                    }
                )
            paused = False
            pause_open = None
            target_due = _parse_iso(payload.get("target_due_at")) or target_due
        elif et == SLA_EVENT_RESOLVE:
            if paused and pause_open is not None:
                intervals.append(
                    {
                        "paused_at": pause_open.isoformat(),
                        "resumed_at": ev.at.isoformat(),
                    }
                )
                paused = False
                pause_open = None
            resolved_at = ev.at

    if pause_open is not None:
        intervals.append({"paused_at": pause_open.isoformat(), "resumed_at": None})

    if target_due is None and fallback_due_at is not None and resolved_at is None:
        target_due = fallback_due_at

    breached = (
        resolved_at is None
        and not paused
        and target_due is not None
        and target_due < now
    )

    if resolved_at is not None:
        status = "resolved"
    elif started_at is None and target_due is None:
        status = "none"
    elif paused:
        status = "paused"
    elif breached:
        status = "breached"
    else:
        status = "running"

    return SlaClockProjection(
        started_at=started_at.isoformat() if started_at else None,
        target_due_at=target_due.isoformat() if target_due else None,
        resolved_at=resolved_at.isoformat() if resolved_at else None,
        paused=paused,
        paused_intervals=intervals,
        breached=breached,
        status=status,
    )


async def list_sla_events(
    db: AsyncSession, *, tenant_id: str, thread_id: str
) -> list[CommunicationThreadSlaEvent]:
    rows = (
        await db.execute(
            select(CommunicationThreadSlaEvent)
            .where(
                CommunicationThreadSlaEvent.tenant_id == tenant_id,
                CommunicationThreadSlaEvent.thread_id == thread_id,
            )
            .order_by(CommunicationThreadSlaEvent.at.asc())
        )
    ).scalars().all()
    return list(rows)


async def append_sla_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    event_type: str,
    actor_user_id: str | None,
    at: datetime | None = None,
    payload: dict[str, Any] | None = None,
) -> CommunicationThreadSlaEvent:
    row = CommunicationThreadSlaEvent(
        id=str(uuid4()),
        tenant_id=tenant_id,
        thread_id=thread_id,
        event_type=event_type,
        at=at or _now(),
        actor_user_id=actor_user_id,
        payload=dict(payload or {}),
    )
    db.add(row)
    return row


async def project_thread_sla(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    now: datetime | None = None,
) -> SlaClockProjection:
    events = await list_sla_events(db, tenant_id=tenant_id, thread_id=str(thread.id))
    return project_sla_clock(
        events, now=now, fallback_due_at=getattr(thread, "sla_due_at", None)
    )


__all__ = [
    "SlaClockProjection",
    "append_sla_event",
    "list_sla_events",
    "project_sla_clock",
    "project_thread_sla",
]
