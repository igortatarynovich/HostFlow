"""P2 — Document Hub consumer bridge to Document Runtime Engine."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.evaluator import (
    evaluate_document_runtime,
    runtime_precedence,
)

SOURCE_LAYER = "document_runtime"


def _norm_doc(code: str) -> str:
    return str(code or "").strip().lower().replace("-", "_")


def _document_type_code(doc: dict[str, Any]) -> str:
    for key in ("document_type_code", "type", "type_code", "doc_type"):
        raw = doc.get(key)
        if raw is not None and str(raw).strip():
            return _norm_doc(str(raw))
    return ""


def index_best_instances_by_type(
    documents: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Pick best current document instance per type using runtime precedence."""
    best_snapshot: dict[str, dict[str, Any]] = {}
    best_rank: dict[str, int] = {}

    for raw in documents or []:
        if not isinstance(raw, dict):
            continue
        code = _document_type_code(raw)
        if not code:
            continue

        runtime = raw.get("document_runtime")
        if not isinstance(runtime, dict):
            runtime = evaluate_document_runtime(raw, document_type_code=code)

        rank = runtime_precedence(runtime)
        if code not in best_snapshot or rank >= best_rank.get(code, 0):
            enriched = dict(raw)
            enriched["document_runtime"] = runtime
            best_snapshot[code] = enriched
            best_rank[code] = rank

    return best_snapshot


def index_best_runtimes_from_evaluation(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, dict[str, Any]]:
    """Resolve best runtime per document type from evaluation + optional snapshots."""
    runtimes_by_type: dict[str, dict[str, Any]] = {}
    ranks: dict[str, int] = {}

    runtime_section = evaluation.get("document_runtime") or {}
    for row in runtime_section.get("documents") or []:
        if not isinstance(row, dict):
            continue
        code = _norm_doc(str(row.get("document_type_code") or ""))
        if not code:
            continue
        rank = runtime_precedence(row)
        if code not in runtimes_by_type or rank >= ranks.get(code, 0):
            runtimes_by_type[code] = row
            ranks[code] = rank

    if documents:
        for code, snapshot in index_best_instances_by_type(documents).items():
            runtime = snapshot.get("document_runtime")
            if not isinstance(runtime, dict):
                continue
            rank = runtime_precedence(runtime)
            if code not in runtimes_by_type or rank >= ranks.get(code, 0):
                runtimes_by_type[code] = runtime
                ranks[code] = rank

    return runtimes_by_type


def resolve_runtime_for_required_type(
    doc_code: str,
    *,
    instances_by_type: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Runtime for a required document type — best instance or canonical missing."""
    code = _norm_doc(doc_code)
    runtime = instances_by_type.get(code)
    if isinstance(runtime, dict):
        return runtime
    return evaluate_document_runtime(None, document_type_code=code)


def _legacy_status_from_runtime(runtime: dict[str, Any]) -> str:
    if runtime.get("satisfies_requirement"):
        return "satisfied"
    signal = str(runtime.get("runtime_signal") or "")
    workflow = str(runtime.get("workflow_status") or "")
    if signal in {"missing"} or workflow == "missing":
        return "missing"
    if signal in {"rejected", "expired"} or workflow == "rejected":
        return "problem"
    if signal in {"pending_verification"} or workflow in {"uploaded", "pending_review"}:
        return "pending"
    return "missing"


def build_checklist_runtime_item(
    *,
    requirement: dict[str, Any],
    runtime: dict[str, Any],
    requirement_source_layer: str = "requirement_engine",
) -> dict[str, Any]:
    """Runtime-aware checklist row for one required document type."""
    doc_code = _norm_doc(str(requirement.get("document_type_code") or runtime.get("document_type_code") or ""))
    return {
        "document_type_code": doc_code,
        "status": _legacy_status_from_runtime(runtime),
        "lifecycle_status": runtime.get("workflow_status"),
        "expiry_status": runtime.get("expiry_status"),
        "satisfies_requirement": bool(runtime.get("satisfies_requirement")),
        "blockers": list(runtime.get("blockers") or []),
        "warnings": list(runtime.get("warnings") or []),
        "document_id": runtime.get("document_id"),
        "document_runtime": runtime,
        "requirement_source_layer": requirement_source_layer,
        "runtime_source_layer": SOURCE_LAYER,
        "source_layer": requirement_source_layer,
        "level": requirement.get("level"),
        "verification": requirement.get("verification"),
        "reason_code": requirement.get("reason_code"),
        "pack_code": requirement.get("pack_code"),
        "source": requirement.get("source"),
        "source_ref": requirement.get("source_ref"),
    }


def build_document_hub_runtime_checklist(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
    requirement_source_layer: str = "requirement_engine",
) -> dict[str, Any]:
    """
    Build Document Hub checklist from Requirement Engine required docs + runtime instances.

    Requirement Engine defines *what* is required; Document Runtime defines *whether*
    the best instance satisfies the requirement.
    """
    instances_by_type = index_best_runtimes_from_evaluation(evaluation, documents=documents)

    checklist_items: list[dict[str, Any]] = []
    satisfied_documents: list[str] = []
    missing_documents: list[str] = []
    pending_documents: list[str] = []
    problem_documents: list[str] = []

    for req in evaluation.get("required_documents") or []:
        if not isinstance(req, dict):
            continue
        doc_code = _norm_doc(str(req.get("document_type_code") or ""))
        if not doc_code:
            continue

        runtime = resolve_runtime_for_required_type(doc_code, instances_by_type=instances_by_type)
        item = build_checklist_runtime_item(
            requirement=req,
            runtime=runtime,
            requirement_source_layer=requirement_source_layer,
        )
        checklist_items.append(item)

        status = item["status"]
        if status == "satisfied":
            satisfied_documents.append(doc_code)
        elif status == "pending":
            pending_documents.append(doc_code)
        elif status == "problem":
            problem_documents.append(doc_code)
        else:
            missing_documents.append(doc_code)

    return {
        "evaluation_version": DOCUMENT_RUNTIME_V1,
        "items": checklist_items,
        "satisfied_documents": sorted(set(satisfied_documents)),
        "missing_documents": sorted(set(missing_documents)),
        "pending_documents": sorted(set(pending_documents)),
        "problem_documents": sorted(set(problem_documents)),
    }


def apply_runtime_checklist_to_hub_section(
    hub_section: dict[str, Any],
    runtime_checklist: dict[str, Any],
) -> dict[str, Any]:
    """Overlay runtime checklist onto Document Hub requirement section."""
    merged = dict(hub_section)
    merged["document_runtime"] = runtime_checklist
    merged["satisfied_documents"] = list(runtime_checklist.get("satisfied_documents") or [])
    merged["missing_documents"] = list(runtime_checklist.get("missing_documents") or [])
    merged["pending_documents"] = list(runtime_checklist.get("pending_documents") or [])
    merged["problem_documents"] = list(runtime_checklist.get("problem_documents") or [])
    merged["satisfied"] = not merged["missing_documents"] and not merged["pending_documents"] and not merged["problem_documents"]

    items_by_code = {
        _norm_doc(str(row.get("document_type_code") or "")): row
        for row in runtime_checklist.get("items") or []
        if isinstance(row, dict)
    }

    required_documents: list[dict[str, Any]] = []
    for req in merged.get("required_documents") or []:
        if not isinstance(req, dict):
            continue
        code = _norm_doc(str(req.get("document_type_code") or ""))
        runtime_item = items_by_code.get(code) or {}
        required_documents.append({**req, **runtime_item})
    merged["required_documents"] = required_documents
    merged["source_layers"] = sorted(
        {
            str(hub_section.get("source_layer") or "requirement_engine"),
            SOURCE_LAYER,
        }
    )
    return merged
