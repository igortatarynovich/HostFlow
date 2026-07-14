"""Evaluation input fingerprint contract (ADR-018 PR 2B-1).

Canonical, order-independent hash of decision-relevant inputs.
Materialization of stored fingerprints is deferred to later PRs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from backend.app.document_types.registry import is_canonical_code, is_runtime_alias


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class EvaluationDocumentFact:
    document_id: str
    document_type_code: str
    document_type_version_id: Optional[str]
    review_status: str
    valid_to: Optional[date]
    schema_valid: bool
    lifecycle_status: str
    document_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        code = _norm(self.document_type_code)
        if is_runtime_alias(code):
            raise ValueError(f"legacy alias not permitted in fingerprint input: {code}")
        if code in {"unclassified", "other"}:
            raise ValueError(f"forbidden evidence type in fingerprint input: {code}")
        if not is_canonical_code(code):
            raise ValueError(f"non-canonical document type in fingerprint input: {code}")

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type_code": _norm(self.document_type_code),
            "document_type_version_id": _norm(self.document_type_version_id) or None,
            "review_status": _norm(self.review_status),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "schema_valid": bool(self.schema_valid),
            "lifecycle_status": _norm(self.lifecycle_status),
            "document_data": _canonicalize_json(self.document_data),
        }


@dataclass(frozen=True)
class EvaluationFingerprintInput:
    policy_ref: str
    policy_version: str
    target_stage: str
    person_facts: dict[str, Any]
    documents: tuple[EvaluationDocumentFact, ...]
    process_states: dict[str, str] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)

    def to_canonical_dict(self) -> dict[str, Any]:
        docs = sorted(
            (doc.to_canonical_dict() for doc in self.documents),
            key=lambda row: row["document_id"],
        )
        return {
            "policy_ref": self.policy_ref,
            "policy_version": self.policy_version,
            "target_stage": _norm(self.target_stage),
            "person_facts": _canonicalize_json(self.person_facts),
            "documents": docs,
            "process_states": _canonicalize_json(self.process_states),
            "overrides": _canonicalize_json(self.overrides),
        }


def _canonicalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _canonicalize_json(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonicalize_json(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def compute_evaluation_input_fingerprint(payload: EvaluationFingerprintInput) -> str:
    """Return stable sha256 hex digest of canonical evaluation inputs."""
    canonical = payload.to_canonical_dict()
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "EvaluationDocumentFact",
    "EvaluationFingerprintInput",
    "compute_evaluation_input_fingerprint",
]
