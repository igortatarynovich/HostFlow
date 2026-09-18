"""Evidence views and delivery contracts (facts for neighbour policy authorities)."""

from __future__ import annotations

from typing import Any

_SOURCE: dict[str, tuple[str, str]] = {
    "APPLICABILITY_REQUIRED": (
        "backend.app.services.document_hub_delivery_contract",
        "APPLICABILITY_REQUIRED",
    ),
    "DocumentApplicabilityContext": (
        "backend.app.services.document_applicability_resolver",
        "DocumentApplicabilityContext",
    ),
    "DocumentApplicabilityResolver": (
        "backend.app.services.document_applicability_resolver",
        "DocumentApplicabilityResolver",
    ),
    "DocumentDataContract": ("backend.app.document_hub.document_data_contract", "DocumentDataContract"),
    "E4_LINKED_ENTITY_TYPE": (
        "backend.app.services.document_hub_delivery_contract",
        "E4_LINKED_ENTITY_TYPE",
    ),
    "RequirementEvaluationInputContract": (
        "backend.app.document_hub.document_data_contract",
        "RequirementEvaluationInputContract",
    ),
    "SOURCE_LAYER": ("backend.app.document_runtime.delivery_contract", "SOURCE_LAYER"),
    "aggregate_document_expiry_states": (
        "backend.app.services.document_expiry_engine",
        "aggregate_document_expiry_states",
    ),
    "apply_runtime_checklist_to_hub_section": (
        "backend.app.document_runtime.hub_bridge",
        "apply_runtime_checklist_to_hub_section",
    ),
    "build_document_data_contract_from_hub_row": (
        "backend.app.document_hub.document_data_contract",
        "build_document_data_contract_from_hub_row",
    ),
    "build_instances_delivery_via_contract": (
        "backend.app.document_runtime.delivery_contract",
        "build_instances_delivery_via_contract",
    ),
    "build_required_documents_delivery_via_contract": (
        "backend.app.document_runtime.delivery_contract",
        "build_required_documents_delivery_via_contract",
    ),
    "build_transition_gate_from_evaluation": (
        "backend.app.document_runtime.pe_bridge",
        "build_transition_gate_from_evaluation",
    ),
    "compute_owner_summary_via_contract": (
        "backend.app.services.document_hub_delivery_contract",
        "compute_owner_summary_via_contract",
    ),
    "enrich_documents_via_contract": (
        "backend.app.document_runtime.delivery_contract",
        "enrich_documents_via_contract",
    ),
    "enrich_snapshot_via_contract": (
        "backend.app.services.document_runtime_delivery_contract",
        "enrich_snapshot_via_contract",
    ),
    "ensure_ruleset_seed_via_contract": (
        "backend.app.services.document_hub_delivery_contract",
        "ensure_ruleset_seed_via_contract",
    ),
    "evaluate_document_expiry": (
        "backend.app.services.document_expiry_engine",
        "evaluate_document_expiry",
    ),
    "evaluate_document_runtime": ("backend.app.document_runtime.evaluator", "evaluate_document_runtime"),
    "evaluate_required_doc_applicability_via_contract": (
        "backend.app.services.document_hub_delivery_contract",
        "evaluate_required_doc_applicability_via_contract",
    ),
    "list_candidate_documents_via_contract": (
        "backend.app.services.document_hub_delivery_contract",
        "list_candidate_documents_via_contract",
    ),
    "load_default_ruleset": ("backend.app.services.document_ruleset", "load_default_ruleset"),
    "map_runtime_to_requirement_items": (
        "backend.app.document_runtime.evaluator",
        "map_runtime_to_requirement_items",
    ),
    "owner_expiry_aggregate_to_dict": (
        "backend.app.services.document_expiry_engine",
        "owner_expiry_aggregate_to_dict",
    ),
    "persist_outstanding_asks_via_contract": (
        "backend.app.services.document_hub_delivery_contract",
        "persist_outstanding_asks_via_contract",
    ),
    "runtime_precedence": ("backend.app.document_runtime.evaluator", "runtime_precedence"),
}

__all__ = sorted(_SOURCE)


def __getattr__(name: str) -> Any:
    if name not in _SOURCE:
        raise AttributeError(name)
    import importlib

    mod_name, attr = _SOURCE[name]
    return getattr(importlib.import_module(mod_name), attr)


def __dir__() -> list[str]:
    return list(__all__)
