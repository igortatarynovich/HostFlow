"""P3 — Process Engine transition gate bridge to Document Runtime Engine."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.hub_bridge import build_document_hub_runtime_checklist

SOURCE_LAYER = "document_runtime"
REQUIREMENT_SOURCE_LAYER = "requirement_engine"


def _norm_doc(code: str) -> str:
    return str(code or "").strip().lower().replace("-", "_")


def _runtime_blocking_reason(
    *,
    runtime: dict[str, Any],
    doc_code: str,
    blocker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = dict(blocker or {})
    return {
        "code": str(base.get("code") or f"document_not_satisfied:{doc_code}"),
        "message": str(base.get("message") or f"Required document not satisfied: {doc_code}"),
        "source_layer": SOURCE_LAYER,
        "document_type_code": doc_code,
        "lifecycle_status": runtime.get("workflow_status"),
        "expiry_status": runtime.get("expiry_status"),
        "satisfies_requirement": bool(runtime.get("satisfies_requirement")),
        "document_runtime": runtime,
    }


def _runtime_warning(
    *,
    runtime: dict[str, Any],
    doc_code: str,
    warning: dict[str, Any],
) -> dict[str, Any]:
    return {
        **warning,
        "source_layer": str(warning.get("source_layer") or SOURCE_LAYER),
        "document_type_code": doc_code,
        "lifecycle_status": runtime.get("workflow_status"),
        "expiry_status": runtime.get("expiry_status"),
        "document_runtime": runtime,
    }


def _field_blocking_reason(row: dict[str, Any]) -> dict[str, Any]:
    qualified = str(row.get("qualified_code") or "").strip()
    return {
        "code": str(row.get("code") or "missing_data_field"),
        "message": str(row.get("message") or f"Required field missing: {qualified}"),
        "source_layer": str(row.get("source_layer") or REQUIREMENT_SOURCE_LAYER),
        "qualified_code": qualified or None,
        "field_code": qualified.split(".")[-1] if qualified else None,
    }


def map_runtime_checklist_to_transition_fragments(
    runtime_checklist: dict[str, Any],
) -> dict[str, Any]:
    """Map document_runtime_v1 checklist to PE transition gate document fragments."""
    blocking_reasons: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    missing_documents: list[str] = []
    pending_documents: list[str] = []
    problem_documents: list[str] = []

    for item in runtime_checklist.get("items") or []:
        if not isinstance(item, dict):
            continue
        doc_code = _norm_doc(str(item.get("document_type_code") or ""))
        if not doc_code:
            continue
        runtime = item.get("document_runtime") if isinstance(item.get("document_runtime"), dict) else {}

        for warning in item.get("warnings") or []:
            if isinstance(warning, dict):
                warnings.append(_runtime_warning(runtime=runtime, doc_code=doc_code, warning=warning))

        if item.get("satisfies_requirement"):
            continue

        status = str(item.get("status") or "")
        if status == "missing":
            missing_documents.append(doc_code)
        elif status == "pending":
            pending_documents.append(doc_code)
        elif status == "problem":
            problem_documents.append(doc_code)
        else:
            missing_documents.append(doc_code)

        blockers = [row for row in (item.get("blockers") or []) if isinstance(row, dict)]
        if blockers:
            for blocker in blockers:
                blocking_reasons.append(
                    _runtime_blocking_reason(runtime=runtime, doc_code=doc_code, blocker=blocker)
                )
        else:
            blocking_reasons.append(_runtime_blocking_reason(runtime=runtime, doc_code=doc_code))

    unsatisfied_documents = sorted(set(missing_documents + pending_documents + problem_documents))
    return {
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "missing_documents": unsatisfied_documents,
        "pending_documents": sorted(set(pending_documents)),
        "problem_documents": sorted(set(problem_documents)),
    }


def build_transition_gate_from_evaluation(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Build PE transition gate payload from Requirement Engine + Document Runtime.

    Requirement Engine defines required document types; Document Runtime decides whether
    the best instance satisfies the gate.
    """
    runtime_checklist = build_document_hub_runtime_checklist(
        evaluation,
        documents=documents,
        requirement_source_layer=REQUIREMENT_SOURCE_LAYER,
    )
    doc_fragments = map_runtime_checklist_to_transition_fragments(runtime_checklist)

    blocking_reasons = list(doc_fragments.get("blocking_reasons") or [])
    warnings = list(doc_fragments.get("warnings") or [])
    missing_data_fields: list[dict[str, str]] = []

    for row in evaluation.get("blockers") or []:
        if not isinstance(row, dict):
            continue
        if row.get("document_type_code"):
            continue
        qualified = str(row.get("qualified_code") or "").strip()
        if not qualified:
            continue
        blocking_reasons.append(_field_blocking_reason(row))
        field_code = qualified.split(".")[-1] if qualified else "unknown"
        missing_data_fields.append({"field_code": field_code, "qualified_code": qualified, "label": qualified})

    for row in evaluation.get("warnings") or []:
        if not isinstance(row, dict):
            continue
        if row.get("document_type_code"):
            continue
        warnings.append(
            {
                "code": str(row.get("code") or "requirement_warning"),
                "message": str(row.get("message") or "Requirement warning"),
                "source_layer": str(row.get("source_layer") or REQUIREMENT_SOURCE_LAYER),
                "qualified_code": row.get("qualified_code"),
                "severity": "warning",
            }
        )

    return {
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "missing_documents": list(doc_fragments.get("missing_documents") or []),
        "pending_documents": list(doc_fragments.get("pending_documents") or []),
        "problem_documents": list(doc_fragments.get("problem_documents") or []),
        "missing_data_fields": missing_data_fields,
        "document_runtime": runtime_checklist,
        "satisfied": bool(evaluation.get("satisfied")),
    }
