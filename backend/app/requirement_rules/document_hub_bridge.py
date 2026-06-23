"""P2C — Document Hub consumer bridge to Requirement Rules Engine."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.requirement_rules.readiness_bridge import (
    READINESS_CONTEXT,
    evaluate_candidate_readiness_requirements,
)

DOCUMENT_HUB_CONTEXT = READINESS_CONTEXT
SOURCE_LAYER = "requirement_engine"


def _norm_doc(code: str) -> str:
    return str(code or "").strip().lower().replace("-", "_")


def map_requirement_evaluation_to_document_hub(
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Map requirement_evaluation_v1 to Document Hub required/missing/satisfied view."""
    blocker_codes = {
        _norm_doc(str(row.get("document_type_code") or ""))
        for row in evaluation.get("blockers") or []
        if isinstance(row, dict) and row.get("document_type_code")
    }
    blocker_codes.discard("")

    required_items: list[dict[str, Any]] = []
    missing_documents: list[str] = []
    satisfied_documents: list[str] = []

    for req in evaluation.get("required_documents") or []:
        if not isinstance(req, dict):
            continue
        doc_code = _norm_doc(str(req.get("document_type_code") or ""))
        if not doc_code:
            continue
        status = "missing" if doc_code in blocker_codes else "satisfied"
        required_items.append(
            {
                "document_type_code": doc_code,
                "status": status,
                "source_layer": SOURCE_LAYER,
                "level": req.get("level"),
                "verification": req.get("verification"),
                "reason_code": req.get("reason_code"),
                "pack_code": req.get("pack_code"),
                "source": req.get("source"),
                "source_ref": req.get("source_ref"),
            }
        )
        if status == "missing":
            missing_documents.append(doc_code)
        else:
            satisfied_documents.append(doc_code)

    return {
        "applied": True,
        "source_layer": SOURCE_LAYER,
        "entity_profile_code": evaluation.get("entity_profile_code"),
        "evaluation_version": evaluation.get("evaluation_version") or REQUIREMENT_EVALUATION_V1,
        "context": evaluation.get("context") or DOCUMENT_HUB_CONTEXT,
        "satisfied": bool(evaluation.get("satisfied")),
        "required_documents": required_items,
        "missing_documents": sorted(set(missing_documents)),
        "satisfied_documents": sorted(set(satisfied_documents)),
        "rule_sources_applied": list(evaluation.get("rule_sources_applied") or []),
    }


def merge_requirement_engine_into_owner_summary(
    summary: dict[str, Any],
    hub_section: dict[str, Any],
) -> dict[str, Any]:
    """Overlay Requirement Engine document requirements on legacy owner summary."""
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
        "problems": 0,
        "problematic": [],
        "in_progress": 0,
        "in_progress_types": [],
    }
    merged["percent_ready"] = 100 if total == 0 else round(100 * ready_count / total)

    if total == 0:
        merged["status"] = merged.get("status") or "no_required"
    elif missing:
        merged["status"] = "missing"
    elif ready_count == total:
        merged["status"] = "ok"
    else:
        merged["status"] = merged.get("status") or "missing"

    checklist = dict(merged.get("checklist") or {})
    checklist["requiredTypes"] = required_codes
    checklist["source_layer"] = SOURCE_LAYER
    merged["checklist"] = checklist
    merged["requirement_engine"] = hub_section
    merged["source_layer"] = SOURCE_LAYER
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
    return map_requirement_evaluation_to_document_hub(evaluation)
