"""DR1-contract — Requirement Engine → Hub outstanding-ask projection.

Seals the read/projection chain from Requirement Engine evaluation to Hub
``outstanding_asks`` rows consumed by ``documents.hub_adapter_v1`` (E7).
No persistence. No mass generation. Runtime creation of asks is DR1-runtime.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_types.registry import is_canonical_code, normalize_input_doc_type
from backend.app.requirement_rules.document_hub_bridge import (
    SOURCE_LAYER,
    map_requirement_evaluation_to_document_hub,
)

CONTRACT_ID = "engine_to_hub_outstanding_ask.v1"
HUB_ADAPTER_ID = "documents.hub_adapter_v1"
OUTSTANDING_ASK_STATES = frozenset({"missing", "requested", "problem"})


def _canonical_doc_type(code: str) -> str:
    return normalize_input_doc_type(code)


def validate_outstanding_ask_row(row: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False
    doc_type = str(row.get("doc_type") or "").strip()
    state = str(row.get("state") or "").strip()
    if not doc_type or state not in OUTSTANDING_ASK_STATES:
        return False
    return is_canonical_code(doc_type)


def hub_section_to_outstanding_asks(hub_section: dict[str, Any]) -> list[dict[str, str]]:
    """Map ``document_hub_bridge`` section to E7 ``outstanding_asks`` rows."""
    if not hub_section.get("applied"):
        return []

    problem_types = {
        _canonical_doc_type(str(code))
        for code in hub_section.get("problem_documents") or []
    }
    pending_types = {
        _canonical_doc_type(str(code))
        for code in hub_section.get("pending_documents") or []
    } - problem_types
    missing_types = {
        _canonical_doc_type(str(code))
        for code in hub_section.get("missing_documents") or []
    } - problem_types - pending_types

    asks: list[dict[str, str]] = []
    for code in sorted(missing_types):
        asks.append({"doc_type": code, "state": "missing"})
    for code in sorted(pending_types):
        asks.append({"doc_type": code, "state": "requested"})
    for code in sorted(problem_types):
        asks.append({"doc_type": code, "state": "problem"})
    return asks


def project_engine_evaluation_to_outstanding_asks(
    evaluation: dict[str, Any],
    *,
    documents: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, str]]:
    """Project Requirement Engine evaluation to Hub outstanding-ask rows."""
    hub_section = map_requirement_evaluation_to_document_hub(
        evaluation,
        documents=documents,
    )
    return hub_section_to_outstanding_asks(hub_section)


def contract_metadata() -> dict[str, str]:
    return {
        "contract_id": CONTRACT_ID,
        "hub_adapter_id": HUB_ADAPTER_ID,
        "source_layer": SOURCE_LAYER,
    }
