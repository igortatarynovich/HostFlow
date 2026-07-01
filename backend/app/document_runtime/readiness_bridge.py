"""P1 — Readiness consumer bridge (delegates to delivery contract)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_runtime.delivery_contract import (
    build_instances_delivery_via_contract,
    enrich_documents_via_contract,
    enrich_snapshot_via_contract,
)

# Backward-compatible aliases for existing imports.
enrich_snapshot_with_runtime = enrich_snapshot_via_contract
enrich_documents_with_runtime = enrich_documents_via_contract
build_document_runtime_section = build_instances_delivery_via_contract

__all__ = [
    "build_document_runtime_section",
    "enrich_documents_with_runtime",
    "enrich_snapshot_with_runtime",
]
