"""Redaction helpers for migration export (no PII / document numbers)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_SENSITIVE_KEY_RE = re.compile(
    r"(number|passport|pesel|nip|email|phone|birth|address|document_data|extracted|custom_name)",
    re.IGNORECASE,
)


def stable_issue_id(*, candidate_id: str, issue_category: str, affected_source: str = "") -> str:
    """Stable identity across dry-runs — run_id must NOT participate."""
    payload = f"{candidate_id}:{issue_category}:{affected_source}"
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def occurrence_id(*, run_id: str, issue_id: str) -> str:
    """Per-run occurrence of a stable issue."""
    payload = f"{run_id}:{issue_id}"
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def redact_document_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": row.get("document_id"),
        "stored_doc_type": row.get("stored_doc_type"),
        "canonical_type_code": row.get("canonical_type_code"),
        "has_legacy_type": row.get("has_legacy_type"),
        "is_unclassified": row.get("is_unclassified"),
        "missing_type_version_id": row.get("missing_type_version_id"),
        "version_assignment_status": row.get("version_assignment_status"),
        "schema_valid": row.get("schema_valid"),
        "schema_error_count": len(row.get("schema_errors") or []),
        "review_status": row.get("review_status"),
    }


def redact_candidate_audit(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["documents"] = [redact_document_audit_row(d) for d in row.get("documents") or []]
    out.pop("evaluation_error", None)
    return out


def contains_sensitive_export(payload: dict[str, Any]) -> bool:
    def walk(value: Any, key: str = "") -> bool:
        if isinstance(value, dict):
            return any(walk(v, k) for k, v in value.items())
        if isinstance(value, list):
            return any(walk(v, key) for v in value)
        if _SENSITIVE_KEY_RE.search(key):
            return True
        return False

    return walk(payload)


__all__ = [
    "contains_sensitive_export",
    "occurrence_id",
    "redact_candidate_audit",
    "redact_document_audit_row",
    "stable_issue_id",
]
