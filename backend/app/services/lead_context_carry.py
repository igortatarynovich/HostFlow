"""Slice 4 Guard 2 — carry lead narrative context onto Candidate at conversion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.audit import log_activity

CONTEXT_CARRIED_ACTION = "lead_to_candidate.context_carried"
LEAD_CONTINUITY_SCHEMA = "lead_continuity_v1"
NOTE_PREFIX = "[From lead]\n"

_INTAKE_SNAPSHOT_KEYS = (
    "status",
    "last_decision",
    "note",
    "summary",
    "confirmed_vacancy_id",
    "reject_reason",
    "pool_id",
)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def resolve_lead_note(lead: Any) -> str:
    """Best-effort lead narrative text (column, normalized, payload, intake)."""
    direct = str(getattr(lead, "note", None) or "").strip()
    if direct:
        return direct

    norm = _as_dict(getattr(lead, "normalized", None))
    for key in ("note", "notes", "recruiter_note", "operator_note"):
        raw = norm.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

    payload = _as_dict(getattr(lead, "payload", None))
    for key in ("note", "notes"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

    intake = norm.get("intake_resolution_v1")
    if isinstance(intake, dict):
        intake_note = str(intake.get("note") or "").strip()
        if intake_note:
            return intake_note

    return ""


def _candidate_extra_dict(candidate: Any) -> dict[str, Any]:
    raw = getattr(candidate, "extra", None)
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _set_candidate_extra(candidate: Any, data: dict[str, Any]) -> None:
    candidate.extra = json.dumps(data or {})


def build_lead_continuity_snapshot(lead: Any) -> dict[str, Any]:
    lead_id = str(getattr(lead, "id", "") or "").strip()
    norm = _as_dict(getattr(lead, "normalized", None))
    note = resolve_lead_note(lead)
    intake_raw = norm.get("intake_resolution_v1")
    intake_dict = intake_raw if isinstance(intake_raw, dict) else None

    carried_fields: list[str] = []
    snapshot: dict[str, Any] = {
        "schema_version": LEAD_CONTINUITY_SCHEMA,
        "source_lead_id": lead_id,
        "carried_at": datetime.now(timezone.utc).isoformat(),
        "carried_fields": carried_fields,
    }

    if note:
        snapshot["lead_note"] = note
        carried_fields.append("lead_note")

    if intake_dict:
        intake_snapshot = {
            key: intake_dict[key]
            for key in _INTAKE_SNAPSHOT_KEYS
            if key in intake_dict and intake_dict[key] not in (None, "")
        }
        if intake_snapshot:
            snapshot["intake_resolution_v1"] = intake_snapshot
            carried_fields.append("intake_resolution_v1")

    stage = str(getattr(lead, "stage", None) or "").strip()
    if stage and stage.lower() not in {"new"}:
        snapshot["lead_stage"] = stage
        carried_fields.append("lead_stage")

    call_raw = norm.get("call_result_v1")
    if isinstance(call_raw, dict):
        result = str(call_raw.get("result") or "").strip()
        if result:
            call_snapshot = {"result": result}
            at = str(call_raw.get("at") or "").strip()
            note = str(call_raw.get("note") or "").strip()
            nxt = str(call_raw.get("next_contact_at") or "").strip()
            actor = str(call_raw.get("by") or "").strip()
            if at:
                call_snapshot["at"] = at
            if note:
                call_snapshot["note"] = note
            if nxt:
                call_snapshot["next_contact_at"] = nxt
            if actor:
                call_snapshot["by"] = actor
            snapshot["call_result_v1"] = call_snapshot
            carried_fields.append("call_result_v1")

    history_raw = norm.get("call_results_v1")
    if isinstance(history_raw, list) and history_raw:
        history = [dict(item) for item in history_raw if isinstance(item, dict) and item.get("result")]
        if history:
            snapshot["call_results_v1"] = history
            if "call_results_v1" not in carried_fields:
                carried_fields.append("call_results_v1")

    return snapshot


async def carry_lead_context_on_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
    candidate: Any,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Persist lead context on candidate; idempotent per source_lead_id."""
    lead_id = str(getattr(lead, "id", "") or "").strip()
    cid = str(getattr(candidate, "id", "") or "").strip()
    if not lead_id or not cid:
        return {"carried": False, "reason": "missing_ids"}

    extra = _candidate_extra_dict(candidate)
    existing = extra.get("lead_continuity_v1")
    if isinstance(existing, dict) and str(existing.get("source_lead_id") or "") == lead_id:
        return {"carried": False, "reason": "already_carried", "snapshot": existing}

    snapshot = build_lead_continuity_snapshot(lead)
    carried_fields = list(snapshot.get("carried_fields") or [])
    extra["source_lead_id"] = lead_id

    if carried_fields:
        extra["lead_continuity_v1"] = snapshot
    else:
        extra["lead_continuity_v1"] = {
            "schema_version": LEAD_CONTINUITY_SCHEMA,
            "source_lead_id": lead_id,
            "carried_at": snapshot["carried_at"],
            "carried_fields": [],
            "link_only": True,
        }

    _set_candidate_extra(candidate, extra)

    lead_note = str(snapshot.get("lead_note") or "").strip()
    if lead_note:
        cand_note = str(getattr(candidate, "note", None) or "").strip()
        if not cand_note:
            candidate.note = f"{NOTE_PREFIX}{lead_note}"
        elif lead_note not in cand_note:
            candidate.note = f"{cand_note}\n\n{NOTE_PREFIX}{lead_note}"

    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=CONTEXT_CARRIED_ACTION,
        target_type="candidate",
        target_id=cid,
        payload={
            "lead_id": lead_id,
            "carried_fields": carried_fields,
            "link_only": not bool(carried_fields),
        },
    )
    await db.flush()

    return {
        "carried": True,
        "carried_fields": carried_fields,
        "snapshot": extra["lead_continuity_v1"],
    }
