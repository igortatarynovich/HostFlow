"""Map RequirementEvaluationResult to API/workspace payloads (PR 2B-3)."""

from __future__ import annotations

from typing import Any

from backend.app.requirement_rules.evaluation.result_contract import (
    RequirementEvaluationResult,
    RequirementEvaluationRow,
    RequirementEvaluationStatus,
)
from backend.app.requirement_rules.requirement_definition_registry import get_requirement_definition_v1


def _norm(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


_FULFILLED_STATUSES = frozenset(
    {
        RequirementEvaluationStatus.fulfilled,
        RequirementEvaluationStatus.not_applicable,
        RequirementEvaluationStatus.not_required_yet,
        RequirementEvaluationStatus.waived,
    }
)


def _row_to_checklist_item(row: RequirementEvaluationRow) -> dict[str, Any]:
    definition = get_requirement_definition_v1(row.requirement_code) or {}
    alternatives = []
    for alt in definition.get("alternatives") or []:
        if not isinstance(alt, dict):
            continue
        alternatives.append(
            {
                "alternative_code": alt.get("alternative_code"),
                "evidence_variant_code": alt.get("alternative_code"),
                "document_type_codes": [alt.get("document_type")] if alt.get("document_type") else [],
            }
        )

    matched_docs = [
        {
            "document_id": ref.document_id,
            "document_type_code": ref.document_type_code,
            "status": ref.review_status,
            "match_role": ref.match_role.value,
            "valid_to": ref.valid_to.isoformat() if ref.valid_to else None,
        }
        for ref in row.matched_documents
    ]

    return {
        "requirement_code": row.requirement_code,
        "public_name": definition.get("public_name"),
        "business_purpose": definition.get("business_purpose"),
        "level": "blocking",
        "accepted_evidence_variants": alternatives,
        "candidate_evidence": None,
        "fulfilled": row.status in _FULFILLED_STATUSES,
        "evaluation": {
            "status": row.status.value,
            "applicability": row.applicability.value,
            "is_blocking": row.is_blocking,
            "matched_alternative": row.matched_alternative,
            "matched_documents": matched_docs,
            "matched_process": row.matched_process.to_dict() if row.matched_process else None,
            "excluded_alternatives": [alt.to_dict() for alt in row.excluded_alternatives],
            "missing_fields": list(row.missing_fields),
            "reasons": [reason.to_dict() for reason in row.reasons],
            "next_action": row.next_action.value,
            "ownership": row.ownership.to_dict() if row.ownership else None,
            "required_by_stage": row.required_by_stage,
            "blocks_stage": row.blocks_stage,
        },
    }


def evaluation_result_to_checklist(result: RequirementEvaluationResult) -> dict[str, Any]:
    items = [_row_to_checklist_item(row) for row in result.requirements]
    pipeline_blockers = evaluation_result_to_pipeline_blockers(result)
    return {
        "candidate_id": result.entity_id,
        "requirements": items,
        "all_fulfilled": pipeline_blockers.get("all_fulfilled"),
        "pipeline_blockers": pipeline_blockers,
        "requirement_evaluation_v2": result.to_dict(),
    }


def evaluation_result_to_pipeline_blockers(result: RequirementEvaluationResult) -> dict[str, Any]:
    missing: list[str] = []
    problematic: list[str] = []
    pending_review: list[str] = []
    unfulfilled: list[dict[str, Any]] = []

    for row in result.requirements:
        if not row.is_blocking:
            continue
        code = row.requirement_code
        row_payload = {
            "requirement_code": code,
            "status": row.status.value,
            "applicability": row.applicability.value,
            "is_blocking": True,
            "matched_alternative": row.matched_alternative,
            "reasons": [reason.to_dict() for reason in row.reasons],
            "next_action": row.next_action.value,
        }
        unfulfilled.append(row_payload)

        if row.status == RequirementEvaluationStatus.pending_review:
            pending_review.append(code)
        elif row.status in {
            RequirementEvaluationStatus.invalid,
            RequirementEvaluationStatus.expired,
        }:
            problematic.append(code)
        else:
            missing.append(code)

    return {
        "source": "requirement_evaluation_v2",
        "all_fulfilled": not unfulfilled,
        "missing_requirements": missing,
        "problematic_requirements": problematic,
        "pending_review_requirements": pending_review,
        "unfulfilled_requirements": unfulfilled,
        "blocking_requirements": list(result.blocking_requirements),
    }


def evaluation_result_to_requirement_gate(result: RequirementEvaluationResult) -> dict[str, Any]:
    blockers = evaluation_result_to_pipeline_blockers(result)
    return {
        "applied": True,
        "satisfied": result.can_transition,
        "policy_ref": result.policy_ref,
        "policy_version": result.policy_version,
        "target_stage": result.target_stage,
        "overall_status": result.overall_status.value,
        "input_fingerprint": result.input_fingerprint,
        "blocking_requirements": list(result.blocking_requirements),
        "missing_requirements": blockers.get("missing_requirements") or [],
        "problematic_requirements": blockers.get("problematic_requirements") or [],
        "pending_review_requirements": blockers.get("pending_review_requirements") or [],
        "requirements": [row.to_dict() for row in result.requirements],
    }


__all__ = [
    "evaluation_result_to_checklist",
    "evaluation_result_to_pipeline_blockers",
    "evaluation_result_to_requirement_gate",
]
