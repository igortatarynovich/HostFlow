"""Lead call-result disposition + operator comments (recruitment intake and B2B).

Persists append-only history in ``normalized.call_results_v1`` and the latest
entry in ``normalized.call_result_v1`` (mirrors ``lead_lost_reason_v1`` style).

Recruitment: saving a result is a first-class activity
(call → outcome → note → actor → timestamp → next_contact_at) and the first
substantive action that moves intake lifecycle new → in_progress.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead
from backend.app.modules.leads import crud, pipeline_hooks
from backend.app.modules.leads.intake_lifecycle import (
    is_recruitment_intake_lead,
    mark_recruitment_intake_in_progress,
)
from backend.app.services.audit import log_activity

CALL_RESULT_VALUES = frozenset(
    {
        "no_answer",
        "answered",
        "callback_requested",
        "interested",
        "not_interested",
        "wrong_number",
        "unavailable",
    }
)

NO_CONTACT_RESULTS = frozenset({"no_answer", "wrong_number", "unavailable"})
CONTACT_REACHED_RESULTS = frozenset(
    {"answered", "callback_requested", "interested", "not_interested"}
)

MAX_CALL_RESULTS_HISTORY = 50


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def apply_lead_call_result(
    lead: Lead,
    *,
    result: str,
    note: Optional[str] = None,
    actor_sub: Optional[str] = None,
    next_contact_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Mutate lead.normalized with a new call-result entry. Returns the entry."""
    result_norm = str(result or "").strip().lower()
    if result_norm not in CALL_RESULT_VALUES:
        raise ValueError(f"Unsupported call result: {result}")

    note_clean = (str(note).strip() if note is not None else "") or None
    if note_clean and len(note_clean) > 2000:
        note_clean = note_clean[:2000]

    now_iso = datetime.now(timezone.utc).isoformat()
    entry: Dict[str, Any] = {
        "result": result_norm,
        "at": now_iso,
    }
    if note_clean:
        entry["note"] = note_clean
    if actor_sub:
        entry["by"] = actor_sub
    if next_contact_at is not None:
        entry["next_contact_at"] = _iso(next_contact_at)

    norm = dict(lead.normalized or {})
    history = norm.get("call_results_v1")
    if not isinstance(history, list):
        history = []
    history = [h for h in history if isinstance(h, dict)]
    history.append(entry)
    if len(history) > MAX_CALL_RESULTS_HISTORY:
        history = history[-MAX_CALL_RESULTS_HISTORY:]
    norm["call_results_v1"] = history
    norm["call_result_v1"] = entry
    lead.normalized = norm
    return entry


async def log_lead_call_result(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    result: str,
    note: Optional[str] = None,
    actor_id: Optional[str] = None,
    bump_stage: bool = True,
    next_contact_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Persist call result + optional note / next contact.

    Recruitment: stamps intake_resolution in_progress (IR is lifecycle authority).
    CRM stage bump is compatibility only (new → contacted).
    """
    prev_stage = getattr(lead, "stage", None)
    entry = apply_lead_call_result(
        lead,
        result=result,
        note=note,
        actor_sub=actor_id,
        next_contact_at=next_contact_at,
    )

    if is_recruitment_intake_lead(lead):
        mark_recruitment_intake_in_progress(
            lead,
            actor=actor_id,
            last_action="call_result",
        )

    await db.flush()

    result_norm = str(entry.get("result") or "")
    stage_changed = False
    new_stage: Optional[str] = None
    current = str(prev_stage or "").strip().lower()

    if bump_stage and current not in {"converted", "lost", "qualified"}:
        if is_recruitment_intake_lead(lead):
            # Any recorded call is substantive work — not a "no answer" pipeline stage.
            if current in {"", "new"}:
                new_stage = "contacted"
        elif result_norm in CONTACT_REACHED_RESULTS and current != "contacted":
            new_stage = "contacted"

    if new_stage:
        await crud.update_lead_stage(db, lead, stage=new_stage)
        stage_changed = str(getattr(lead, "stage", None) or "") != str(prev_stage or "")
        if stage_changed:
            await pipeline_hooks.record_lead_stage_change(
                db,
                tenant_id=tenant_id,
                lead=lead,
                from_stage=prev_stage,
                to_stage=new_stage,
                actor_id=actor_id,
            )

    await log_activity(
        db,
        tenant_id=tenant_id,
        action="lead.call_result",
        actor_id=actor_id,
        target_type="lead",
        target_id=str(lead.id),
        payload={
            "call": True,
            "outcome": entry.get("result"),
            "result": entry.get("result"),
            "note": entry.get("note"),
            "actor": actor_id,
            "timestamp": entry.get("at"),
            "next_contact_at": entry.get("next_contact_at"),
            "stage_after": getattr(lead, "stage", None),
            "stage_changed": stage_changed,
        },
    )

    if next_contact_at is not None and actor_id:
        try:
            from backend.app.services import reminder_tasks

            due = next_contact_at
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            await reminder_tasks.create_reminder(
                db,
                tenant_id=tenant_id,
                actor_id=actor_id,
                payload={
                    "title": "Call back lead",
                    "type": "custom",
                    "entity_type": "lead",
                    "entity_id": str(lead.id),
                    "assignee_id": actor_id,
                    "priority": "normal",
                    "channel": "internal",
                    "due_at": due,
                    "payload": {
                        "source": "lead_call_result",
                        "result": result_norm,
                    },
                },
            )
        except Exception:
            pass

    return entry
