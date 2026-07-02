"""A3-B4 — Operational (activity-type) requirements for Requirements Workspace."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead, Reminder
from backend.app.models.activity import ActivityStatus
from backend.app.models.audit import ActivityLog
from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.operational_catalog import (
    get_operational_requirement_definition,
    operational_requirements_for_profile,
)
from backend.app.services.lead_first_contact_continuity import (
    FIRST_CONTACT_SUPPRESSED_ACTION,
    lead_first_contact_suppression_reasons,
)

FULFILLMENTS_EXTRA_KEY = "operational_requirement_fulfillments"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_extra_dict(candidate: Candidate) -> dict[str, Any]:
    data = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return data if isinstance(data, dict) else {}


def _persist_candidate_extra(candidate: Candidate, data: dict[str, Any]) -> None:
    if hasattr(candidate, "_set_extra"):
        candidate._set_extra(data)
    else:
        import json

        candidate.extra = json.dumps(data or {})


def _manual_fulfillment(candidate: Candidate, requirement_code: str) -> dict[str, Any] | None:
    extra = _candidate_extra_dict(candidate)
    rows = extra.get(FULFILLMENTS_EXTRA_KEY)
    if not isinstance(rows, dict):
        return None
    row = rows.get(_norm(requirement_code))
    return row if isinstance(row, dict) else None


def _serialize_operational_row(
    definition: dict[str, Any],
    *,
    status: str,
    activity_id: str | None = None,
    satisfied_via: str | None = None,
    continuity_reasons: list[str] | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    code = _norm(definition.get("requirement_code"))
    cta = definition.get("cta") if isinstance(definition.get("cta"), dict) else {}
    return {
        "requirement_code": code,
        "type": _norm(definition.get("type")) or "activity",
        "public_name": definition.get("public_name") or code,
        "level": definition.get("level") or "blocking",
        "status": status,
        "activity_id": activity_id,
        "satisfied_via": satisfied_via,
        "continuity_reasons": list(continuity_reasons or []),
        "completed_at": completed_at,
        "cta": {
            "action": cta.get("action") or "call",
            "default_activity_type": cta.get("default_activity_type") or "call",
        },
    }


async def _find_satisfying_candidate_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    definition: dict[str, Any],
) -> Reminder | None:
    activity_types = {
        _norm(item)
        for item in (definition.get("activity_types") or [])
        if _norm(item)
    }
    completion_statuses = {
        _norm(item)
        for item in (definition.get("completion_statuses") or ["done"])
        if _norm(item)
    }
    if not activity_types:
        return None

    stmt = (
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.related_entity_type == "candidate",
            Reminder.related_entity_id == str(candidate_id),
            Reminder.type.in_(sorted(activity_types)),
            Reminder.status.in_(sorted(completion_statuses)),
        )
        .order_by(Reminder.completed_at.desc().nullslast(), Reminder.updated_at.desc())
        .limit(1)
    )
    return await db.scalar(stmt)


async def _lead_continuity_satisfies_first_contact(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> tuple[bool, list[str]]:
    """True when lead-side touch or suppression marker implies first contact already happened."""
    lead = await db.scalar(
        select(Lead).where(
            Lead.tenant_id == tenant_id,
            Lead.candidate_id == str(candidate_id),
        ).limit(1)
    )
    if lead is not None:
        reasons = await lead_first_contact_suppression_reasons(db, tenant_id=tenant_id, lead=lead)
        if reasons:
            return True, reasons

    suppressed = await db.scalar(
        select(ActivityLog.id).where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_type == "candidate",
            ActivityLog.target_id == str(candidate_id),
            ActivityLog.action == FIRST_CONTACT_SUPPRESSED_ACTION,
        ).limit(1)
    )
    if suppressed is not None:
        return True, ["activity_log:first_contact_suppressed"]

    return False, []


async def evaluate_operational_requirement_row(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    definition: dict[str, Any],
) -> dict[str, Any]:
    code = _norm(definition.get("requirement_code"))
    manual = _manual_fulfillment(candidate, code)
    if manual:
        return _serialize_operational_row(
            definition,
            status="satisfied",
            activity_id=_norm(manual.get("activity_id")) or None,
            satisfied_via=_norm(manual.get("via")) or "manual",
            completed_at=_norm(manual.get("completed_at")) or None,
        )

    if code == "first_contact_completed":
        satisfied, reasons = await _lead_continuity_satisfies_first_contact(
            db,
            tenant_id=tenant_id,
            candidate_id=str(candidate.id),
        )
        if satisfied:
            return _serialize_operational_row(
                definition,
                status="satisfied",
                satisfied_via="lead_continuity",
                continuity_reasons=reasons,
                completed_at=_now_iso(),
            )

    activity = await _find_satisfying_candidate_activity(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        definition=definition,
    )
    if activity is not None:
        completed_at = activity.completed_at.isoformat() if getattr(activity, "completed_at", None) else None
        return _serialize_operational_row(
            definition,
            status="satisfied",
            activity_id=str(activity.id),
            satisfied_via="activity",
            completed_at=completed_at,
        )

    return _serialize_operational_row(definition, status="open")


async def evaluate_operational_requirements_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    entity_profile_code: str | None,
) -> list[dict[str, Any]]:
    definitions = operational_requirements_for_profile(entity_profile_code)
    rows: list[dict[str, Any]] = []
    for definition in definitions:
        rows.append(
            await evaluate_operational_requirement_row(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
                definition=definition,
            )
        )
    return rows


async def complete_operational_requirement_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    requirement_code: str,
    activity_id: str,
    user_id: str,
) -> dict[str, Any]:
    code = _norm(requirement_code)
    definition = get_operational_requirement_definition(code)
    if definition is None:
        raise ValueError("unknown_operational_requirement")
    if _norm(definition.get("type")) != "activity":
        raise ValueError("not_activity_requirement")

    activity = await db.get(Reminder, str(activity_id))
    if activity is None or str(activity.tenant_id) != str(tenant_id):
        raise ValueError("activity_not_found")
    if str(getattr(activity, "related_entity_type", "") or "") != "candidate":
        raise ValueError("activity_not_candidate_scoped")
    if str(getattr(activity, "related_entity_id", "") or "") != str(candidate.id):
        raise ValueError("activity_wrong_candidate")

    allowed_types = {
        _norm(item)
        for item in (definition.get("activity_types") or [])
        if _norm(item)
    }
    activity_type = _norm(getattr(activity, "type", None))
    if allowed_types and activity_type not in allowed_types:
        raise ValueError("activity_type_not_allowed")

    if _norm(getattr(activity, "status", None)) != ActivityStatus.done:
        now = datetime.now(timezone.utc)
        activity.status = ActivityStatus.done
        activity.completed_at = now
        activity.updated_at = now

    extra = _candidate_extra_dict(candidate)
    fulfillments = extra.get(FULFILLMENTS_EXTRA_KEY)
    if not isinstance(fulfillments, dict):
        fulfillments = {}
    fulfillments[code] = {
        "activity_id": str(activity.id),
        "via": "manual",
        "completed_at": _now_iso(),
        "completed_by_user_id": _norm(user_id) or None,
    }
    extra[FULFILLMENTS_EXTRA_KEY] = fulfillments
    _persist_candidate_extra(candidate, extra)
    await db.flush()

    return await evaluate_operational_requirement_row(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
        definition=definition,
    )


__all__ = [
    "FULFILLMENTS_EXTRA_KEY",
    "complete_operational_requirement_activity",
    "evaluate_operational_requirement_row",
    "evaluate_operational_requirements_for_candidate",
]
