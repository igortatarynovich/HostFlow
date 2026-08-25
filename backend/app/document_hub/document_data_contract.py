"""DocumentData runtime contract — Hub facts normalized for Requirement Evaluation (ADR-018 PR 2A).

Evaluation MUST consume only DocumentDataContract instances. Legacy ``meta`` fields are
read exclusively by the Hub adapter at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from backend.app.document_types.registry import normalize_input_doc_type
from backend.app.document_types.schema_registry import (
    normalize_raw_to_document_data,
    validate_document_data,
)


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
class DocumentEntityLink:
    owner_type: str
    owner_id: str
    relation_type: str = "primary"


@dataclass(frozen=True)
class DocumentDataContract:
    document_id: str
    document_type_code: str
    document_type_id: Optional[str]
    document_type_version_id: Optional[str]
    document_data: dict[str, Any]
    review_status: str
    valid_from: Optional[date]
    valid_to: Optional[date]
    issuing_country: Optional[str]
    schema_valid: bool
    schema_errors: tuple[str, ...]
    entity_links: tuple[DocumentEntityLink, ...] = field(default_factory=tuple)
    lifecycle_status: str = "active"

    @property
    def is_approved(self) -> bool:
        return _norm(self.review_status) == "approved"


@dataclass(frozen=True)
class RequirementEvaluationInputContract:
    """Explicit evaluator input contract (PR 2A — implementation in PR 2B)."""

    entity_type: str
    entity_id: str
    policy_ref: str
    target_stage: str
    evaluation_date: date
    person_facts: dict[str, Any]
    documents: tuple[DocumentDataContract, ...]
    process_state: Optional[str] = None


FORBIDDEN_EVALUATION_SOURCES = frozenset(
    {
        "meta.extracted_fields",
        "meta.fields",
        "legacy_doc_type",
        "custom_name",
        "aliases",
        "owner_summary",
        "candidate_evidence_manual",
    }
)


def _merge_raw_sources(meta: dict[str, Any]) -> dict[str, Any]:
    merged = dict(meta or {})
    extracted = meta.get("extracted_fields") or meta.get("fields")
    if isinstance(extracted, dict):
        for key, value in extracted.items():
            merged.setdefault(key, value)
    return merged


def build_document_data_contract_from_hub_row(
    doc: Any,
    *,
    canonical_type_code: Optional[str] = None,
    ref_type_code: Optional[str] = None,
) -> DocumentDataContract:
    """Hub adapter: Document ORM row → normalized DocumentDataContract."""
    doc_id = str(getattr(doc, "id", "") or "")
    module_doc_type = _norm(getattr(doc, "doc_type", ""))
    canonical = _norm(canonical_type_code or ref_type_code or normalize_input_doc_type(module_doc_type))

    meta = getattr(doc, "meta", None) or {}
    if not isinstance(meta, dict):
        meta = {}

    raw = _merge_raw_sources(meta)
    document_data = normalize_raw_to_document_data(canonical, raw)

    status_raw = getattr(doc, "status", None)
    review_status = status_raw.value if hasattr(status_raw, "value") else str(status_raw or "")

    valid_to = _parse_date(getattr(doc, "expire_date", None)) or _parse_date(document_data.get("expiry_date"))
    valid_from = _parse_date(document_data.get("valid_from") or document_data.get("issue_date"))
    issuing_country = document_data.get("issuing_country") or document_data.get("country")

    schema_valid, schema_errors = validate_document_data(canonical, document_data)

    candidate_id = str(getattr(doc, "candidate_id", "") or "")
    links: list[DocumentEntityLink] = []
    if candidate_id:
        links.append(DocumentEntityLink(owner_type="candidate", owner_id=candidate_id, relation_type="primary"))

    return DocumentDataContract(
        document_id=doc_id,
        document_type_code=canonical,
        document_type_id=str(getattr(doc, "document_type_id", "") or "") or None,
        document_type_version_id=str(getattr(doc, "document_type_version_id", "") or "") or None,
        document_data=document_data,
        review_status=review_status,
        valid_from=valid_from,
        valid_to=valid_to,
        issuing_country=str(issuing_country) if issuing_country else None,
        schema_valid=schema_valid,
        schema_errors=tuple(schema_errors),
        entity_links=tuple(links),
        lifecycle_status="superseded" if meta.get("superseded") or meta.get("replaced") else "active",
    )


__all__ = [
    "DocumentDataContract",
    "DocumentEntityLink",
    "FORBIDDEN_EVALUATION_SOURCES",
    "RequirementEvaluationInputContract",
    "build_document_data_contract_from_hub_row",
]
