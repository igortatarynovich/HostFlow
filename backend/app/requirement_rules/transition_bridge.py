"""P2B/P3 — Process Engine transition gate bridge (Requirement Engine + Document Runtime)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_runtime.pe_bridge import (
    SOURCE_LAYER as RUNTIME_SOURCE_LAYER,
    build_transition_gate_from_evaluation,
)
from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.readiness_bridge import (
    build_requirement_engine_section,
    evaluate_candidate_requirements,
    load_candidate_documents_snapshot,
)

READY_FOR_HANDOFF_STAGE = "ready_for_handoff"
READY_FOR_HANDOFF_GATE_CODE = "ready_for_handoff_gate"
TRANSITION_CONTEXT = "transition"
REQUIREMENT_SOURCE_LAYER = "requirement_engine"


def is_ready_for_handoff_gate(target_system_stage: str | None) -> bool:
    return str(target_system_stage or "").strip().lower() == READY_FOR_HANDOFF_STAGE


def map_requirement_evaluation_to_transition_gate(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Map requirement_evaluation_v1 + document_runtime_v1 to PE transition gate payload."""
    runtime_gate = build_transition_gate_from_evaluation(evaluation, documents=documents)
    requirement_engine = build_requirement_engine_section(evaluation)

    return {
        "applied": True,
        "satisfied": bool(runtime_gate.get("satisfied")),
        "entity_profile_code": evaluation.get("entity_profile_code"),
        "evaluation_version": evaluation.get("evaluation_version"),
        "context": evaluation.get("context") or TRANSITION_CONTEXT,
        "stage_code": evaluation.get("stage_code"),
        "transition_code": evaluation.get("transition_code"),
        "process_profile_code": evaluation.get("process_profile_code"),
        "blocking_reasons": list(runtime_gate.get("blocking_reasons") or []),
        "warnings": list(runtime_gate.get("warnings") or []),
        "missing_documents": list(runtime_gate.get("missing_documents") or []),
        "pending_documents": list(runtime_gate.get("pending_documents") or []),
        "problem_documents": list(runtime_gate.get("problem_documents") or []),
        "missing_data_fields": list(runtime_gate.get("missing_data_fields") or []),
        "document_runtime": runtime_gate.get("document_runtime"),
        "requirement_engine": requirement_engine,
        "source_layers": sorted({REQUIREMENT_SOURCE_LAYER, RUNTIME_SOURCE_LAYER}),
    }


def merge_transition_requirement_gate(
    report: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    """Overlay Requirement Engine + Document Runtime gate on transfer policy report."""
    merged = dict(report)
    source_layers = set(merged.get("source_layers") or [])
    source_layers.update(gate.get("source_layers") or [REQUIREMENT_SOURCE_LAYER, RUNTIME_SOURCE_LAYER])
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
    merged["document_runtime"] = gate.get("document_runtime")
    merged["requirement_gate"] = {
        "applied": True,
        "satisfied": bool(gate.get("satisfied")),
        "context": gate.get("context") or TRANSITION_CONTEXT,
        "entity_profile_code": gate.get("entity_profile_code"),
        "stage_code": gate.get("stage_code"),
        "transition_code": gate.get("transition_code"),
        "process_profile_code": gate.get("process_profile_code"),
        "document_runtime": gate.get("document_runtime"),
        "source_layers": list(gate.get("source_layers") or [REQUIREMENT_SOURCE_LAYER, RUNTIME_SOURCE_LAYER]),
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
        stage_code=READY_FOR_HANDOFF_STAGE,
        transition_code=READY_FOR_HANDOFF_GATE_CODE,
    )
    if evaluation is None:
        return None

    documents = await load_candidate_documents_snapshot(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate_id=str(cand.id),
    )
    return map_requirement_evaluation_to_transition_gate(evaluation, documents=documents)
