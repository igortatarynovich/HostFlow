"""Lead activity timeline (combined ActivityLog + Reminder events).

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
god-module split, step 5/N). Re-exported via ``service/__init__.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ActivityLog, Lead, Reminder
from backend.app.modules.leads.schemas import LeadTimelineEventOut, LeadTimelineResponse


async def get_lead_timeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    limit: int = 200,
) -> LeadTimelineResponse:
    # Ensure lead exists and belongs to tenant.
    lead_row = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id).limit(1))
    lead = lead_row.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # ActivityLog events for this lead.
    log_rows = (
        await db.execute(
            select(ActivityLog.action, ActivityLog.created_at, ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.target_type == "lead",
                ActivityLog.target_id == lead_id,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        )
    ).all()

    # Reminder events for this lead.
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
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id == lead_id,
            )
            .order_by(Reminder.created_at.desc())
            .limit(limit)
        )
    ).all()

    events: list[LeadTimelineEventOut] = []

    for action, created_at, payload in log_rows:
        kind = "activity"
        source = "activity_log"
        title = str(action or "").strip() or "event"
        descr = None
        if action == "lead.stage_changed":
            kind = "stage_changed"
            from_stage = (payload or {}).get("from_stage") if isinstance(payload, dict) else None
            to_stage = (payload or {}).get("to_stage") if isinstance(payload, dict) else None
            descr = f"{from_stage or '—'} → {to_stage or '—'}"
        elif action == "lead.questionnaire_email_sent":
            kind = "questionnaire_email"
            if isinstance(payload, dict):
                recipient = payload.get("recipient") or "—"
                channel = payload.get("channel") or "email"
                link = payload.get("questionnaire_url") or ""
                descr = f"{channel} → {recipient}" + (f" · {link}" if link else "")
        elif action == "lead.questionnaire_email_failed":
            kind = "questionnaire_email"
            if isinstance(payload, dict):
                descr = str(payload.get("error") or payload.get("error_code") or "send failed")
        elif action == "lead.questionnaire_submitted":
            kind = "questionnaire_submitted"
            if isinstance(payload, dict):
                contact = payload.get("contact_name") or "—"
                company = payload.get("company_name") or "—"
                descr = f"{contact} — {company}"
        elif str(action or "").startswith("analytics.next_action."):
            kind = "next_action_warning"
        elif str(action or "").startswith("analytics.perf."):
            kind = "analytics"
        events.append(
            LeadTimelineEventOut(
                at=created_at,
                kind=kind,
                source=source,
                title=title,
                description=descr,
                payload=payload if isinstance(payload, dict) else {},
            )
        )

    for (
        rem_id,
        r_type,
        status,
        title,
        description,
        created_at,
        due_at,
        completed_at,
    ) in rem_rows:
        base_payload: Dict[str, Any] = {
            "reminder_id": rem_id,
            "type": r_type,
            "status": status,
            "due_at": due_at.isoformat() if isinstance(due_at, datetime) else None,
            "completed_at": completed_at.isoformat() if isinstance(completed_at, datetime) else None,
        }
        # Created event
        events.append(
            LeadTimelineEventOut(
                at=created_at,
                kind="reminder_created",
                source="reminder",
                title=title or "Reminder created",
                description=description,
                payload=base_payload,
            )
        )
        # Completed event (if any)
        if completed_at:
            events.append(
                LeadTimelineEventOut(
                    at=completed_at,
                    kind="reminder_completed",
                    source="reminder",
                    title=title or "Reminder completed",
                    description=description,
                    payload=base_payload,
                )
            )

    # Sort all events by time desc and trim.
    events.sort(key=lambda e: e.at, reverse=True)
    if len(events) > limit:
        events = events[:limit]

    return LeadTimelineResponse(items=events)
