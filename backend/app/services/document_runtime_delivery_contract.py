"""Service-layer facade for Document Runtime delivery contract."""

from __future__ import annotations

from backend.app.document_runtime.delivery_contract import (
    SOURCE_LAYER,
    build_instances_delivery_via_contract,
    build_required_documents_delivery_via_contract,
    enrich_documents_via_contract,
    enrich_snapshot_via_contract,
    evaluate_snapshot_via_contract,
    index_best_instances_by_type_via_contract,
    index_best_runtimes_by_type_via_contract,
    resolve_required_type_runtime_via_contract,
    runtime_for_type_via_contract,
)

__all__ = [
    "SOURCE_LAYER",
    "build_instances_delivery_via_contract",
    "build_required_documents_delivery_via_contract",
    "enrich_documents_via_contract",
    "enrich_snapshot_via_contract",
    "evaluate_snapshot_via_contract",
    "index_best_instances_by_type_via_contract",
    "index_best_runtimes_by_type_via_contract",
    "resolve_required_type_runtime_via_contract",
    "runtime_for_type_via_contract",
]
