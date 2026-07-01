"""Shared candidate unified timeline query (ActivityLog + Reminder rows)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import ActivityLog
from backend.app.models.reminder import Reminder


async def fetch_candidate_timeline_events(
    db: AsyncSession,
    tenant_id_str: str,
    candidate_id: str,
    limit: int,
):
    """Return timeline rows newest-first, capped at *limit* (same semantics as GET /candidates/:id/timeline)."""
    from backend.app.api.v1.candidates.schemas import CandidateTimelineEventOut

    log_rows = (
        await db.execute(
            select(ActivityLog.action, ActivityLog.created_at, ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id_str,
                ActivityLog.target_type == "candidate",
                ActivityLog.target_id == str(candidate_id),
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        )
    ).all()

    rem_rows = (
        await db.execute(
            select(
                Reminder.id,
                Reminder.type,
                Reminder.status,
                Reminder.title,
                Reminder.description,
                Reminder.created_at,
                Reminder.due_at,
                Reminder.completed_at,
            )
            .where(
                Reminder.tenant_id == tenant_id_str,
                Reminder.entity_type == "candidate",
                Reminder.entity_id == str(candidate_id),
            )
            .order_by(Reminder.created_at.desc())
            .limit(limit)
        )
    ).all()

    events: list[CandidateTimelineEventOut] = []

    for action, created_at, payload in log_rows:
        kind = "activity"
        title = str(action or "").strip() or "event"
        descr = None
        if str(action or "") in {"candidate.stage_changed", "candidate_stage_changed"}:
            kind = "stage_changed"
        events.append(
            CandidateTimelineEventOut(
                at=created_at,
                kind=kind,
                source="activity_log",
                title=title,
                description=descr,
                payload=payload if isinstance(payload, dict) else {},
            )
        )

    for rem_id, r_type, status, title, description, created_at, due_at, completed_at in rem_rows:
        base_payload: dict = {
            "reminder_id": rem_id,
            "type": r_type,
            "status": status,
            "due_at": due_at.isoformat() if isinstance(due_at, datetime) else None,
            "completed_at": completed_at.isoformat() if isinstance(completed_at, datetime) else None,
        }
        events.append(
            CandidateTimelineEventOut(
                at=created_at,
                kind="reminder_created",
                source="reminder",
                title=title or "Reminder created",
                description=description,
                payload=base_payload,
            )
        )
        if completed_at:
            events.append(
                CandidateTimelineEventOut(
                    at=completed_at,
                    kind="reminder_completed",
                    source="reminder",
                    title=title or "Reminder completed",
                    description=description,
                    payload=base_payload,
                )
            )

    events.sort(key=lambda e: e.at, reverse=True)
    if len(events) > limit:
        events = events[:limit]
    return events
