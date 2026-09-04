"""P2C/P2 — Document Hub consumer bridge (Requirement Engine + Document Runtime)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_runtime.delivery_contract import (
    SOURCE_LAYER as RUNTIME_SOURCE_LAYER,
    build_required_documents_delivery_via_contract,
)
from backend.app.document_runtime.hub_bridge import apply_runtime_checklist_to_hub_section
from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.requirement_rules.readiness_bridge import (
    READINESS_CONTEXT,
    evaluate_candidate_readiness_requirements,
    load_candidate_documents_snapshot,
)

DOCUMENT_HUB_CONTEXT = READINESS_CONTEXT
SOURCE_LAYER = "requirement_engine"


def _norm_doc(code: str) -> str:
    return str(code or "").strip().lower().replace("-", "_")


def map_requirement_evaluation_to_document_hub(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Map requirement_evaluation_v1 + document_runtime_v1 to Document Hub view."""
    runtime_checklist = build_required_documents_delivery_via_contract(
        evaluation,
        documents=documents,
        requirement_source_layer=SOURCE_LAYER,
    )

    hub_section: dict[str, Any] = {
        "applied": True,
        "source_layer": SOURCE_LAYER,
        "entity_profile_code": evaluation.get("entity_profile_code"),
        "evaluation_version": evaluation.get("evaluation_version") or REQUIREMENT_EVALUATION_V1,
        "context": evaluation.get("context") or DOCUMENT_HUB_CONTEXT,
        "satisfied": bool(evaluation.get("satisfied")),
        "required_documents": list(evaluation.get("required_documents") or []),
        "missing_documents": list(runtime_checklist.get("missing_documents") or []),
        "satisfied_documents": list(runtime_checklist.get("satisfied_documents") or []),
        "rule_sources_applied": list(evaluation.get("rule_sources_applied") or []),
    }

    return apply_runtime_checklist_to_hub_section(hub_section, runtime_checklist)


def apply_hub_requirements_to_checklist(
    checklist: dict[str, Any],
    hub_section: dict[str, Any],
) -> dict[str, Any]:
    """Attach runtime-aware required-doc checklist items."""
    if not hub_section.get("applied"):
        return checklist

    merged = dict(checklist)
    required_codes = [
        str(row.get("document_type_code") or "")
        for row in hub_section.get("required_documents") or []
        if isinstance(row, dict) and row.get("document_type_code")
    ]
    existing = [
        str(code).strip()
        for code in (checklist.get("requiredTypes") or [])
        if str(code).strip()
    ]
    # RPM-3B: Hub orchestration must not replace the R5 required-set.
    merged["requiredTypes"] = existing or required_codes
    merged["source_layer"] = hub_section.get("source_layer") or SOURCE_LAYER
    merged["source_layers"] = list(hub_section.get("source_layers") or [SOURCE_LAYER, RUNTIME_SOURCE_LAYER])

    runtime_section = hub_section.get("document_runtime") or {}
    merged["document_runtime"] = runtime_section
    merged["runtimeItems"] = list(runtime_section.get("items") or [])
    return merged


def merge_requirement_engine_into_owner_summary(
    summary: dict[str, Any],
    hub_section: dict[str, Any],
) -> dict[str, Any]:
    """Overlay Requirement Engine + Document Runtime on legacy owner summary."""
    if not hub_section.get("applied"):
        return summary

    merged = dict(summary)
    required_codes = [
        str(row.get("document_type_code") or "")
        for row in hub_section.get("required_documents") or []
        if isinstance(row, dict) and row.get("document_type_code")
    ]
    missing = list(hub_section.get("missing_documents") or [])
    satisfied = list(hub_section.get("satisfied_documents") or [])
    pending = list(hub_section.get("pending_documents") or [])
    problems = list(hub_section.get("problem_documents") or [])

    total = len(required_codes)
    ready_count = len(satisfied)
    merged["required"] = {
        **(merged.get("required") or {}),
        "total": total,
        "ready": ready_count,
        "approved": ready_count,
        "missing_count": len(missing),
        "missing": missing,
        "ready_types": satisfied,
        "missing_types": missing,
        "problems": len(problems) + len(pending),
        "problematic": sorted(set(problems + pending)),
        "in_progress": len(pending),
        "in_progress_types": pending,
    }
    merged["percent_ready"] = 100 if total == 0 else round(100 * ready_count / total)

    if total == 0:
        merged["status"] = merged.get("status") or "no_required"
    elif missing or problems or pending:
        merged["status"] = "missing" if missing else "attention"
    elif ready_count == total:
        merged["status"] = "ok"
    else:
        merged["status"] = merged.get("status") or "missing"

    checklist = apply_hub_requirements_to_checklist(dict(merged.get("checklist") or {}), hub_section)
    merged["checklist"] = checklist
    merged["requirement_engine"] = hub_section
    merged["document_runtime"] = hub_section.get("document_runtime")
    merged["source_layer"] = hub_section.get("source_layer") or SOURCE_LAYER
    merged["source_layers"] = list(hub_section.get("source_layers") or [SOURCE_LAYER, RUNTIME_SOURCE_LAYER])
    return merged


async def evaluate_candidate_document_hub_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[dict[str, Any]]:
    """Evaluate document requirements for Document Hub; None → legacy fallback."""
    evaluation = await evaluate_candidate_readiness_requirements(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate=candidate,
    )
    if evaluation is None:
        return None

    documents = await load_candidate_documents_snapshot(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate_id=str(candidate.id),
    )
    return map_requirement_evaluation_to_document_hub(evaluation, documents=documents)
