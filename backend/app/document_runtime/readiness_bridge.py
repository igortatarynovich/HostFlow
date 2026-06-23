"""P1 — Readiness consumer bridge to Document Runtime Engine."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.evaluator import evaluate_document_runtime


def enrich_snapshot_with_runtime(
    snapshot: dict[str, Any],
    *,
    expiry_required: bool = False,
) -> dict[str, Any]:
    """Attach ``document_runtime_v1`` to a document snapshot."""
    enriched = dict(snapshot)
    runtime = evaluate_document_runtime(
        enriched,
        document_type_code=str(enriched.get("document_type_code") or enriched.get("type") or ""),
        expiry_required=expiry_required,
    )
    enriched["document_runtime"] = runtime
    return enriched


def enrich_documents_with_runtime(
    documents: list[dict[str, Any]],
    *,
    expiry_required_by_type: Optional[dict[str, bool]] = None,
) -> list[dict[str, Any]]:
    """Evaluate runtime for each document snapshot."""
    expiry_map = expiry_required_by_type or {}
    result: list[dict[str, Any]] = []
    for raw in documents or []:
        if not isinstance(raw, dict):
            continue
        doc_type = str(
            raw.get("document_type_code") or raw.get("type") or raw.get("doc_type") or ""
        ).strip().lower()
        result.append(
            enrich_snapshot_with_runtime(
                raw,
                expiry_required=bool(expiry_map.get(doc_type, False)),
            )
        )
    return result


def build_document_runtime_section(documents: list[dict[str, Any]]) -> dict[str, Any]:
    """Build document_runtime_v1 section for Readiness / requirement evaluation."""
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
