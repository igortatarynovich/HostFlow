"""P2 — Document Hub consumer bridge (delegates to delivery contract)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_runtime.delivery_contract import (
    SOURCE_LAYER,
    build_required_document_item_via_contract,
    build_required_documents_delivery_via_contract,
    index_best_instances_by_type_via_contract,
    index_best_runtimes_by_type_via_contract,
    legacy_status_from_runtime_via_contract,
    resolve_required_type_runtime_via_contract,
)

# Backward-compatible aliases for existing imports.
index_best_instances_by_type = index_best_instances_by_type_via_contract
index_best_runtimes_from_evaluation = index_best_runtimes_by_type_via_contract
resolve_runtime_for_required_type = resolve_required_type_runtime_via_contract
_legacy_status_from_runtime = legacy_status_from_runtime_via_contract
build_checklist_runtime_item = build_required_document_item_via_contract
build_document_hub_runtime_checklist = build_required_documents_delivery_via_contract


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
    merged["satisfied"] = (
        not merged["missing_documents"]
        and not merged["pending_documents"]
        and not merged["problem_documents"]
    )

    items_by_code = {
        str(row.get("document_type_code") or "").strip().lower().replace("-", "_"): row
        for row in runtime_checklist.get("items") or []
        if isinstance(row, dict)
    }

    required_documents: list[dict[str, Any]] = []
    for req in merged.get("required_documents") or []:
        if not isinstance(req, dict):
            continue
        code = str(req.get("document_type_code") or "").strip().lower().replace("-", "_")
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
