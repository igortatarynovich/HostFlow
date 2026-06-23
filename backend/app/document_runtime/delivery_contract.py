"""Document Runtime Engine P4 — unified delivery contract (single source of truth)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.evaluator import (
    evaluate_document_runtime,
    runtime_precedence,
)

SOURCE_LAYER = "document_runtime"
REQUIREMENT_SOURCE_LAYER = "requirement_engine"


def _norm_doc(code: str) -> str:
    return str(code or "").strip().lower().replace("-", "_")


def _document_type_code(doc: dict[str, Any]) -> str:
    for key in ("document_type_code", "type", "type_code", "doc_type"):
        raw = doc.get(key)
        if raw is not None and str(raw).strip():
            return _norm_doc(str(raw))
    return ""


def evaluate_snapshot_via_contract(
    snapshot: dict[str, Any] | None,
    *,
    document_type_code: str | None = None,
    expiry_required: bool = False,
) -> dict[str, Any]:
    """Canonical ``document_runtime_v1`` for one document instance snapshot."""
    doc_type = document_type_code or (_document_type_code(snapshot) if snapshot else "")
    return evaluate_document_runtime(
        snapshot,
        document_type_code=doc_type,
        expiry_required=expiry_required,
    )


def enrich_snapshot_via_contract(
    snapshot: dict[str, Any],
    *,
    expiry_required: bool = False,
) -> dict[str, Any]:
    """Attach canonical ``document_runtime_v1`` to a document snapshot."""
    enriched = dict(snapshot)
    existing = enriched.get("document_runtime")
    if isinstance(existing, dict) and existing.get("evaluation_version") == DOCUMENT_RUNTIME_V1:
        return enriched
    runtime = evaluate_snapshot_via_contract(
        enriched,
        document_type_code=str(enriched.get("document_type_code") or enriched.get("type") or ""),
        expiry_required=expiry_required,
    )
    enriched["document_runtime"] = runtime
    return enriched


def enrich_documents_via_contract(
    documents: list[dict[str, Any]],
    *,
    expiry_required_by_type: Optional[dict[str, bool]] = None,
) -> list[dict[str, Any]]:
    """Evaluate runtime for each document snapshot through the delivery contract."""
    expiry_map = expiry_required_by_type or {}
    result: list[dict[str, Any]] = []
    for raw in documents or []:
        if not isinstance(raw, dict):
            continue
        doc_type = _document_type_code(raw)
        result.append(
            enrich_snapshot_via_contract(
                raw,
                expiry_required=bool(expiry_map.get(doc_type, False)),
            )
        )
    return result


def build_instances_delivery_via_contract(
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Delivery DTO: all document instance runtimes."""
    runtimes = [
        row.get("document_runtime")
        for row in documents
        if isinstance(row, dict) and isinstance(row.get("document_runtime"), dict)
    ]
    return {
        "evaluation_version": DOCUMENT_RUNTIME_V1,
        "documents": runtimes,
        "evaluated_count": len(runtimes),
    }


def index_best_instances_by_type_via_contract(
    documents: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Best current document instance per type using runtime precedence."""
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
            runtime = evaluate_snapshot_via_contract(raw, document_type_code=code)

        rank = runtime_precedence(runtime)
        if code not in best_snapshot or rank >= best_rank.get(code, 0):
            enriched = dict(raw)
            enriched["document_runtime"] = runtime
            best_snapshot[code] = enriched
            best_rank[code] = rank

    return best_snapshot


def index_best_runtimes_by_type_via_contract(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, dict[str, Any]]:
    """Best runtime per document type from evaluation delivery + optional snapshots."""
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
        enriched = enrich_documents_via_contract(documents)
        for code, snapshot in index_best_instances_by_type_via_contract(enriched).items():
            runtime = snapshot.get("document_runtime")
            if not isinstance(runtime, dict):
                continue
            rank = runtime_precedence(runtime)
            if code not in runtimes_by_type or rank >= ranks.get(code, 0):
                runtimes_by_type[code] = runtime
                ranks[code] = rank

    return runtimes_by_type


def resolve_required_type_runtime_via_contract(
    doc_code: str,
    *,
    instances_by_type: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Canonical runtime for a required document type — best instance or missing."""
    code = _norm_doc(doc_code)
    runtime = instances_by_type.get(code)
    if isinstance(runtime, dict):
        return runtime
    return evaluate_snapshot_via_contract(None, document_type_code=code)


def legacy_status_from_runtime_via_contract(runtime: dict[str, Any]) -> str:
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


def build_required_document_item_via_contract(
    *,
    requirement: dict[str, Any],
    runtime: dict[str, Any],
    requirement_source_layer: str = REQUIREMENT_SOURCE_LAYER,
) -> dict[str, Any]:
    """Delivery DTO row for one required document type."""
    doc_code = _norm_doc(str(requirement.get("document_type_code") or runtime.get("document_type_code") or ""))
    return {
        "document_type_code": doc_code,
        "status": legacy_status_from_runtime_via_contract(runtime),
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


def build_required_documents_delivery_via_contract(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
    requirement_source_layer: str = REQUIREMENT_SOURCE_LAYER,
) -> dict[str, Any]:
    """
    Delivery DTO: required document types with best-instance runtime.

    Requirement Engine defines *what* is required; this contract defines *whether*
    the best instance satisfies the requirement — identically for all consumers.
    """
    instances_by_type = index_best_runtimes_by_type_via_contract(evaluation, documents=documents)

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

        runtime = resolve_required_type_runtime_via_contract(
            doc_code,
            instances_by_type=instances_by_type,
        )
        item = build_required_document_item_via_contract(
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


def runtime_for_type_via_contract(
    evaluation: dict[str, Any],
    *,
    document_type_code: str,
    documents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Resolve canonical runtime for one required document type across consumers."""
    delivery = build_required_documents_delivery_via_contract(evaluation, documents=documents)
    code = _norm_doc(document_type_code)
    for item in delivery.get("items") or []:
        if isinstance(item, dict) and _norm_doc(str(item.get("document_type_code") or "")) == code:
            runtime = item.get("document_runtime")
            if isinstance(runtime, dict):
                return runtime
    return evaluate_snapshot_via_contract(None, document_type_code=code)
