"""Lead activity timeline (combined ActivityLog + Reminder events).

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
god-module split, step 5/N). Re-exported via ``service/__init__.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ActivityLog, Lead, Reminder
from backend.app.modules.leads.schemas import LeadTimelineEventOut, LeadTimelineResponse

# Recruitment-module audit actions. Sales chronology must not mix candidate process.
_SALES_HIDDEN_ACTIVITY_ACTIONS = frozenset(
    {
        "lead.communication.application_received_sent",
        "lead.communication.rejection_sent",
        "lead.communication.moving_forward_sent",
        "lead.communication.failed",
    }
)
_SALES_HIDDEN_ACTIVITY_PREFIXES = (
    "lead.communication.",
    "analytics.next_action.",
    "analytics.perf.",
)
_SALES_HIDDEN_REMINDER_TYPES = frozenset(
    {
        "leads_no_next_action",
        "leads_stuck_stage",
    }
)


def _is_sales_operator_lead(lead: Lead) -> bool:
    from backend.app.modules.leads.intake_route import is_sales_intake_target
    from backend.app.modules.leads.service.intake_decision import is_client_lead

    if is_client_lead(lead):
        return True
    if str(getattr(lead, "lead_type", "") or "").strip().lower() == "client":
        return True
    return is_sales_intake_target(str(getattr(lead, "lead_target_type", "") or ""))


def _hide_activity_on_sales_timeline(action: str) -> bool:
    raw = str(action or "").strip()
    if raw in _SALES_HIDDEN_ACTIVITY_ACTIONS:
        return True
    return any(raw.startswith(prefix) for prefix in _SALES_HIDDEN_ACTIVITY_PREFIXES)


def _hide_reminder_on_sales_timeline(reminder_type: str, title: Optional[str]) -> bool:
    if str(reminder_type or "").strip() in _SALES_HIDDEN_REMINDER_TYPES:
        return True
    return str(title or "").strip().lower().startswith("lead: create next action")


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

    sales_timeline = _is_sales_operator_lead(lead)

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
        if sales_timeline and _hide_activity_on_sales_timeline(str(action or "")):
            continue
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
        elif action == "lead.call_result":
            kind = "call_result"
            result = (payload or {}).get("result") if isinstance(payload, dict) else None
            note = (payload or {}).get("note") if isinstance(payload, dict) else None
            parts = [str(result)] if result else []
            if note:
                parts.append(str(note))
            descr = " — ".join(parts) if parts else None
        elif action in {"lead.created", "lead.received", "lead.ingested", "lead.imported"}:
            kind = "lead_received"
            if isinstance(payload, dict) and payload.get("source"):
                descr = str(payload.get("source"))
            else:
                descr = str(getattr(lead, "source", None) or "") or None
        elif str(action or "").startswith("analytics.next_action."):
            kind = "next_action_warning"
        elif str(action or "").startswith("analytics.perf."):
            kind = "analytics"
        elif sales_timeline and action in {"rodo_sent", "rodo_sent_failed"}:
            kind = "gdpr_notice" if action == "rodo_sent" else "gdpr_notice_failed"
            title = kind
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
        if sales_timeline and _hide_reminder_on_sales_timeline(str(r_type or ""), title):
            continue
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
    # Always surface lead arrival: Meta/webhook ingest often never writes ActivityLog,
    # so a brand-new lead would otherwise show an empty timeline.
    created_at = getattr(lead, "created_at", None)
    if isinstance(created_at, datetime):
        has_ingest = any(
            str(action or "").strip().lower()
            in {"lead.created", "lead.received", "lead.ingested", "lead.imported"}
            for action, _, _ in log_rows
        )
        if not has_ingest:
            source = str(getattr(lead, "source", None) or "").strip() or None
            lead_type = str(getattr(lead, "lead_type", None) or "").strip() or None
            events.append(
                LeadTimelineEventOut(
                    at=created_at,
                    kind="lead_received",
                    source="lead",
                    title="lead.received",
                    description=source,
                    payload={
                        "source": source,
                        "lead_type": lead_type,
                        "lead_target_type": str(getattr(lead, "lead_target_type", None) or "") or None,
                        "synthetic": True,
                    },
                )
            )

    events.sort(key=lambda e: e.at, reverse=True)
    if len(events) > limit:
        events = events[:limit]

    return LeadTimelineResponse(items=events)
