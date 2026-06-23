"""P2B — Process Engine transition gate bridge to Requirement Rules Engine."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.readiness_bridge import (
    build_requirement_engine_section,
    evaluate_candidate_requirements,
    map_requirement_evaluation_to_package_fragments,
)

READY_FOR_HANDOFF_STAGE = "ready_for_handoff"
TRANSITION_CONTEXT = "transition"


def is_ready_for_handoff_gate(target_system_stage: str | None) -> bool:
    return str(target_system_stage or "").strip().lower() == READY_FOR_HANDOFF_STAGE


def map_requirement_evaluation_to_transition_gate(
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Map requirement_evaluation_v1 to PE transition gate payload."""
    fragments = map_requirement_evaluation_to_package_fragments(evaluation)
    return {
        "applied": True,
        "satisfied": bool(evaluation.get("satisfied")),
        "entity_profile_code": evaluation.get("entity_profile_code"),
        "evaluation_version": evaluation.get("evaluation_version"),
        "context": evaluation.get("context") or TRANSITION_CONTEXT,
        "blocking_reasons": list(fragments.get("blocking_reasons") or []),
        "warnings": list(fragments.get("warnings") or []),
        "missing_documents": list(fragments.get("missing_documents") or []),
        "missing_data_fields": list(fragments.get("missing_data_fields") or []),
        "requirement_engine": build_requirement_engine_section(evaluation),
    }


def merge_transition_requirement_gate(
    report: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    """Overlay Requirement Engine gate result on transfer policy report."""
    merged = dict(report)
    source_layers = set(merged.get("source_layers") or [])
    source_layers.add("requirement_engine")
    merged["source_layers"] = sorted(source_layers)

    blocking_reasons = list(merged.get("blocking_reasons") or [])
    warnings = list(merged.get("warnings") or [])

    for reason in gate.get("blocking_reasons") or []:
        if isinstance(reason, dict):
            blocking_reasons.append(reason)
    for warning in gate.get("warnings") or []:
        if isinstance(warning, dict):
            warnings.append(warning)

    merged["blocking_reasons"] = blocking_reasons
    merged["warnings"] = warnings

    if gate.get("missing_documents"):
        merged["missing_documents"] = sorted(
            set(list(merged.get("missing_documents") or []) + list(gate["missing_documents"]))
        )
    if gate.get("missing_data_fields"):
        seen = {str(row.get("field_code") or "") for row in merged.get("missing_data_fields") or []}
        extra_fields = list(merged.get("missing_data_fields") or [])
        for row in gate["missing_data_fields"]:
            if not isinstance(row, dict):
                continue
            fc = str(row.get("field_code") or "")
            if fc and fc not in seen:
                extra_fields.append(row)
                seen.add(fc)
        merged["missing_data_fields"] = extra_fields

    merged["requirement_engine"] = gate.get("requirement_engine")
    merged["requirement_gate"] = {
        "applied": True,
        "satisfied": bool(gate.get("satisfied")),
        "context": gate.get("context") or TRANSITION_CONTEXT,
        "entity_profile_code": gate.get("entity_profile_code"),
    }

    if not gate.get("satisfied"):
        merged["transfer_allowed"] = False
        merged["handoff_create_allowed"] = False
        merged["ready"] = False
        merged["package_ready"] = False

    return merged


async def evaluate_ready_for_handoff_requirement_gate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> Optional[dict[str, Any]]:
    """Evaluate ready_for_handoff requirement gate; None → legacy fallback."""
    cand = (
        await db.execute(
            select(Candidate).where(
                Candidate.id == str(candidate_id).strip(),
                Candidate.tenant_id == str(tenant_id).strip(),
                Candidate.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if cand is None:
        return None

    evaluation = await evaluate_candidate_requirements(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate=cand,
        context=TRANSITION_CONTEXT,
    )
    if evaluation is None:
        return None
    return map_requirement_evaluation_to_transition_gate(evaluation)
