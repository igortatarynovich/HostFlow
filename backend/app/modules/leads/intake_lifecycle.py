"""Recruitment lead intake lifecycle — one projection over ``intake_resolution_v1``.

Operator funnel: **new → in_progress → terminal decision**.

Terminal outcomes: converted | rejected | pool | duplicate_review.

CRM ``Lead.stage`` is a compatibility projection only. Do not treat it as a
second source of truth for recruitment intake filters, KPI, or UI.

This module does **not** introduce a fourth persisted state machine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from backend.app.models import Lead

INTAKE_LIFECYCLE_VALUES: tuple[str, ...] = (
    "new",
    "in_progress",
    "converted",
    "rejected",
    "pool",
    "duplicate_review",
)

INTAKE_QUEUE_FILTERS: tuple[str, ...] = (
    "new",
    "in_progress",
    "needs_decision",
    "pool",
    "completed",
)

# Legacy GET /leads?intake_lane= values → queue filter.
INTAKE_LANE_ALIASES: dict[str, str] = {
    "to_call": "new",
    "called": "in_progress",
    "rejected": "completed",
    "duplicate": "needs_decision",
    "converted": "completed",
    "pool": "pool",
}

INTAKE_LIFECYCLE_FILTER_WHITELIST: frozenset[str] = frozenset(INTAKE_QUEUE_FILTERS) | frozenset(
    INTAKE_LANE_ALIASES.keys()
)

TERMINAL_IR_STATUS: frozenset[str] = frozenset(
    {
        "rejected",
        "pooled",
        "converted",
        "duplicate_review_requested",
        "duplicate_review",
    }
)

IN_PROGRESS_IR_STATUS: frozenset[str] = frozenset(
    {"in_progress", "qualified", "info_requested"}
)

_COMPAT_STAGE_CONTACTED = "contacted"


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _ir_block(normalized: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = _as_dict(normalized).get("intake_resolution_v1")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _ir_status(normalized: Mapping[str, Any] | None) -> str:
    return str(_ir_block(normalized).get("status") or "").strip().lower()


def is_recruitment_intake_lead(lead: Lead) -> bool:
    lt = str(getattr(lead, "lead_type", "") or "").strip().lower()
    ltt = str(getattr(lead, "lead_target_type", "") or "").strip().lower()
    if lt == "client" or ltt in {"client_lead", "service_order_lead", "partner_lead"}:
        return False
    return True


def _has_call_result(normalized: Mapping[str, Any] | None) -> bool:
    block = _as_dict(normalized).get("call_result_v1")
    if not isinstance(block, Mapping):
        return False
    return bool(str(block.get("result") or "").strip())


def _has_operator_note(lead: Lead, normalized: Mapping[str, Any] | None) -> bool:
    if str(getattr(lead, "note", None) or "").strip():
        return True
    n = _as_dict(normalized)
    for key in ("note", "notes", "recruiter_note", "operator_note"):
        raw = n.get(key)
        if isinstance(raw, str) and raw.strip():
            return True
    ir_note = str(_ir_block(n).get("note") or "").strip()
    return bool(ir_note)


def _rodo_operator_sent(normalized: Mapping[str, Any] | None) -> bool:
    """True when a recruiter (not ingest auto-trigger) sent or marked RODO."""
    rodo = _as_dict(normalized).get("rodo")
    if not isinstance(rodo, Mapping):
        return False
    status = str(rodo.get("status") or "").strip().lower()
    if status == "source_provided":
        return True
    if status != "sent":
        return False
    auto = str(rodo.get("auto_trigger") or "").strip()
    return not auto


def resolve_intake_lifecycle_filter(raw: str | None) -> str | None:
    """Normalize query param (new filter names or legacy intake_lane aliases)."""
    key = str(raw or "").strip().lower()
    if not key:
        return None
    if key in INTAKE_QUEUE_FILTERS:
        return key
    return INTAKE_LANE_ALIASES.get(key)


def project_recruitment_intake_lifecycle(lead: Lead) -> str:
    """Single UI / KPI / filter projection for a recruitment intake lead."""
    if getattr(lead, "candidate_id", None):
        return "converted"

    n = _as_dict(getattr(lead, "normalized", None))
    ir_st = _ir_status(n)
    lead_status = str(getattr(lead, "status", "") or "").strip().lower()
    stage = str(getattr(lead, "stage", "") or "").strip().lower()

    if ir_st == "rejected" or lead_status == "rejected":
        return "rejected"
    if ir_st in {"pooled", "pool"} or n.get("recruitment_pool_intent_v1") is True:
        if not getattr(lead, "candidate_id", None):
            return "pool"
    if (
        lead_status == "duplicate_review"
        or ir_st in {"duplicate_review", "duplicate_review_requested"}
    ):
        return "duplicate_review"
    if ir_st == "converted" or stage == "converted":
        return "converted"
    if ir_st in IN_PROGRESS_IR_STATUS:
        return "in_progress"

    if _has_call_result(n) or _has_operator_note(lead, n) or _rodo_operator_sent(n):
        return "in_progress"

    # Compatibility: CRM contacted/qualified without an IR stamp still means worked.
    if stage in {"contacted", "qualified"}:
        return "in_progress"

    return "new"


def ensure_recruitment_intake_new(normalized: dict[str, Any]) -> None:
    """Stamp ``intake_resolution_v1.status=new`` when the block is absent (ingest)."""
    if not isinstance(normalized, dict):
        return
    existing = normalized.get("intake_resolution_v1")
    if isinstance(existing, Mapping) and str(existing.get("status") or "").strip():
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    normalized["intake_resolution_v1"] = {
        "status": "new",
        "reason_code": None,
        "decided_at": now_iso,
        "decided_by": None,
        "note": None,
        "last_decision": None,
    }


def mark_recruitment_intake_in_progress(
    lead: Lead,
    *,
    actor: Optional[str] = None,
    last_action: Optional[str] = None,
) -> bool:
    """First substantive action → in_progress. Opening the card is not this.

    Returns True when the stamp was applied (including already in_progress updates).
    Terminal IR statuses are left untouched.
    """
    if not is_recruitment_intake_lead(lead):
        return False
    if getattr(lead, "candidate_id", None):
        return False

    n = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    ir = _ir_block(n)
    st = str(ir.get("status") or "").strip().lower()
    if st in TERMINAL_IR_STATUS:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    actor_s = str(actor).strip() if actor else None
    action_s = str(last_action).strip() if last_action else None

    if st in IN_PROGRESS_IR_STATUS:
        if action_s:
            ir["last_action"] = action_s
            ir["updated_at"] = now_iso
            if actor_s:
                ir["updated_by"] = actor_s
            n["intake_resolution_v1"] = ir
            lead.normalized = n
        return True

    n["intake_resolution_v1"] = {
        "status": "in_progress",
        "reason_code": ir.get("reason_code"),
        "decided_at": now_iso,
        "decided_by": actor_s or ir.get("decided_by"),
        "note": ir.get("note"),
        "last_decision": ir.get("last_decision") or action_s,
        "last_action": action_s,
    }
    lead.normalized = n

    stage = str(getattr(lead, "stage", "") or "").strip().lower()
    if stage in {"", "new"}:
        lead.stage = _COMPAT_STAGE_CONTACTED
    return True


def stamp_recruitment_intake_converted(
    lead: Lead,
    *,
    actor: Optional[str] = None,
) -> None:
    """Terminal convert — IR authority + CRM stage compatibility."""
    n = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    ir = _ir_block(n)
    now_iso = datetime.now(timezone.utc).isoformat()
    n["intake_resolution_v1"] = {
        "status": "converted",
        "reason_code": ir.get("reason_code"),
        "decided_at": now_iso,
        "decided_by": str(actor).strip() if actor else ir.get("decided_by"),
        "note": ir.get("note"),
        "last_decision": "convert",
        "last_action": "convert",
    }
    lead.normalized = n
    lead.stage = "converted"


__all__ = [
    "INTAKE_LANE_ALIASES",
    "INTAKE_LIFECYCLE_FILTER_WHITELIST",
    "INTAKE_LIFECYCLE_VALUES",
    "INTAKE_QUEUE_FILTERS",
    "ensure_recruitment_intake_new",
    "is_recruitment_intake_lead",
    "mark_recruitment_intake_in_progress",
    "project_recruitment_intake_lifecycle",
    "resolve_intake_lifecycle_filter",
    "stamp_recruitment_intake_converted",
]
