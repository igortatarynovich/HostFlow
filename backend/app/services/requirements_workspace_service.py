"""A3 — Requirements workspace bundle (checklist + fields + handoff preview)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.requirement_rules.readiness_bridge import (
    build_normalized_payload_from_candidate,
    evaluate_candidate_readiness_requirements,
    resolve_entity_profile_code_for_candidate,
)
from backend.app.services.candidate_evidence_service import build_requirements_checklist
from backend.app.services.operational_requirements_service import (
    evaluate_operational_requirements_for_candidate,
)
from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    is_recruitment_recruiter_write_locked_by_handoff,
)

WORKSPACE_SCHEMA_VERSION = "requirements_workspace_v1"
READY_FOR_HANDOFF_STAGE = "ready_for_handoff"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _payload_has_value(payload: dict[str, Any], qualified_code: str) -> bool:
    raw = payload.get(qualified_code)
    if raw is None:
        return False
    if isinstance(raw, str):
        return bool(raw.strip())
    if isinstance(raw, (list, dict)):
        return bool(raw)
    return True


def build_field_requirements_section(
    evaluation: Optional[dict[str, Any]],
    *,
    normalized_payload: dict[str, Any],
) -> dict[str, Any]:
    """Map requirement_evaluation_v1 required_fields to workspace field_requirements."""
    if not evaluation:
        return {
            "required_fields": [],
            "missing_count": 0,
            "satisfied": True,
        }

    blocker_codes = {
        _norm(row.get("qualified_code"))
        for row in evaluation.get("blockers") or []
        if isinstance(row, dict) and _norm(row.get("qualified_code"))
    }

    required_fields: list[dict[str, Any]] = []
    missing_count = 0
    for row in evaluation.get("required_fields") or []:
        if not isinstance(row, dict):
            continue
        qualified_code = _norm(row.get("qualified_code") or row.get("target"))
        if not qualified_code:
            continue
        satisfied = qualified_code not in blocker_codes and _payload_has_value(
            normalized_payload, qualified_code
        )
        if not satisfied:
            missing_count += 1
        current_value = normalized_payload.get(qualified_code)
        if current_value is not None and not isinstance(current_value, (str, int, float, bool)):
            current_value = str(current_value)
        required_fields.append(
            {
                "qualified_code": qualified_code,
                "level": row.get("level") or "blocking",
                "reason_code": row.get("reason_code"),
                "satisfied": satisfied,
                "current_value": current_value if satisfied else None,
            }
        )

    return {
        "required_fields": required_fields,
        "missing_count": missing_count,
        "satisfied": missing_count == 0,
    }


def build_transfer_readiness_section(report: dict[str, Any]) -> dict[str, Any]:
    """Compact transfer readiness for workspace UI."""
    section: dict[str, Any] = {
        "transfer_allowed": bool(report.get("transfer_allowed")),
        "handoff_create_allowed": bool(report.get("handoff_create_allowed")),
        "blocking_reasons": list(report.get("blocking_reasons") or []),
        "warnings": list(report.get("warnings") or []),
        "destinations_allowed": list(report.get("destinations_allowed") or []),
        "policy_version": report.get("policy_version"),
        "source_layers": list(report.get("source_layers") or []),
    }
    if isinstance(report.get("requirement_engine"), dict):
        section["requirement_engine"] = report["requirement_engine"]
    if isinstance(report.get("requirement_gate"), dict):
        section["requirement_gate"] = report["requirement_gate"]
    return section


def build_workspace_summary(
    *,
    checklist: dict[str, Any],
    field_requirements: dict[str, Any],
    transfer_readiness: dict[str, Any],
    operational_requirements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    requirements = checklist.get("requirements") or []
    applicable = [
        item
        for item in requirements
        if isinstance(item, dict)
        and (item.get("evaluation") or {}).get("status") != "not_applicable"
    ]
    fulfilled_count = sum(
        1
        for item in applicable
        if item.get("fulfilled")
        or (item.get("evaluation") or {}).get("status") == "not_applicable"
    )
    pipeline_blockers = checklist.get("pipeline_blockers") if isinstance(checklist.get("pipeline_blockers"), dict) else {}
    pending_review_count = len(pipeline_blockers.get("pending_review_requirements") or [])
    blocking_open_count = len(pipeline_blockers.get("unfulfilled_requirements") or [])
    if not blocking_open_count:
        blocking_open_count = len(pipeline_blockers.get("missing_requirements") or [])

    all_doc_slots_fulfilled = bool(checklist.get("all_fulfilled"))
    fields_satisfied = bool(field_requirements.get("satisfied"))
    ops_rows = operational_requirements or []
    open_ops = [row for row in ops_rows if isinstance(row, dict) and row.get("status") != "satisfied"]
    ops_open_count = len(open_ops)
    ops_fulfilled = sum(
        1 for row in ops_rows if isinstance(row, dict) and row.get("status") == "satisfied"
    )
    all_fulfilled = all_doc_slots_fulfilled and fields_satisfied and ops_open_count == 0

    return {
        "total_requirements": len(applicable)
        + len(field_requirements.get("required_fields") or [])
        + len(ops_rows),
        "fulfilled_count": fulfilled_count
        + sum(1 for row in field_requirements.get("required_fields") or [] if row.get("satisfied"))
        + ops_fulfilled,
        "blocking_open_count": blocking_open_count
        + int(field_requirements.get("missing_count") or 0)
        + ops_open_count,
        "pending_review_count": pending_review_count,
        "all_fulfilled": all_fulfilled,
        "handoff_ready": bool(transfer_readiness.get("transfer_allowed")),
    }


async def build_requirements_workspace(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    user_role: str | None = None,
) -> dict[str, Any]:
    """Compose requirements_workspace_v1 for Candidate Requirements Workspace UI."""
    tenant_str = str(tenant_id).strip()
    checklist = await build_requirements_checklist(db, tenant_id=tenant_str, candidate=candidate)

    entity_profile_code = await resolve_entity_profile_code_for_candidate(
        db,
        tenant_id=tenant_str,
        candidate=candidate,
    )
    normalized_payload = build_normalized_payload_from_candidate(candidate)
    requirement_evaluation = await evaluate_candidate_readiness_requirements(
        db,
        tenant_id=tenant_str,
        candidate=candidate,
    )
    field_requirements = build_field_requirements_section(
        requirement_evaluation,
        normalized_payload=normalized_payload,
    )

    transfer_report = await TransitionEvaluatorAdapter.evaluate_transition(
        db,
        tenant_id=tenant_str,
        module=RECRUITMENT_MODULE,
        entity_type="candidate",
        entity_id=str(candidate.id),
        target_system_stage=READY_FOR_HANDOFF_STAGE,
        require_destination=False,
        include_engine_metadata=False,
    )
    transfer_readiness = build_transfer_readiness_section(transfer_report)

    operational_requirements = await evaluate_operational_requirements_for_candidate(
        db,
        tenant_id=tenant_str,
        candidate=candidate,
        entity_profile_code=entity_profile_code,
    )

    role = _norm(user_role)
    locked, _lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
        db,
        agency_tenant_id=tenant_str,
        candidate_id=str(candidate.id),
    )
    can_edit = not locked or role in RECRUITMENT_LOCK_OVERRIDE_ROLES

    pipeline_blockers = checklist.get("pipeline_blockers")
    if not isinstance(pipeline_blockers, dict):
        pipeline_blockers = {}

    summary = build_workspace_summary(
        checklist=checklist,
        field_requirements=field_requirements,
        transfer_readiness=transfer_readiness,
        operational_requirements=operational_requirements,
    )

    return {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "candidate_id": str(candidate.id),
        "entity_profile_code": entity_profile_code,
        "vacancy_id": str(candidate.vacancy_id) if getattr(candidate, "vacancy_id", None) else None,
        "can_edit": can_edit,
        "summary": summary,
        "checklist": checklist,
        "field_requirements": field_requirements,
        "requirement_evaluation": requirement_evaluation,
        "transfer_readiness": transfer_readiness,
        "pipeline_blockers": pipeline_blockers,
        "operational_requirements": operational_requirements,
        "evaluated_at": _now_iso(),
    }


__all__ = [
    "WORKSPACE_SCHEMA_VERSION",
    "build_field_requirements_section",
    "build_requirements_workspace",
    "build_transfer_readiness_section",
    "build_workspace_summary",
]
