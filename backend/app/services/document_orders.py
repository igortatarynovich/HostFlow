from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.services.document_catalog import normalize_doc_type


ORDERABLE_CODES: set[str] = {"work_permit", "driver_certificate"}

# Keep in sync with owner_summary.READY_STATUSES — evidence uploads must not
# block ready_for_handoff when files exist but row status lags formal approval.
READY_ORDER_STATUSES: set[DocumentStatus] = {
    DocumentStatus.approved,
    DocumentStatus.received,
    DocumentStatus.delivered,
    DocumentStatus.completed,
    DocumentStatus.submitted,
    DocumentStatus.verified,
    DocumentStatus.uploaded,
    DocumentStatus.issued,
    DocumentStatus.registered,
    DocumentStatus.active,
    DocumentStatus.not_required,
}

# Physical doc rows that satisfy a checklist *required* token (canonical keys).
SATISFYING_TYPES: Dict[str, set[str]] = {
    "driver_license": {"driver_license", "driver_license_code95"},
    "code95": {"code95", "driver_license_code95"},
    # Combined slot: driver_license alone is enough; code95 alone is not (see unit tests).
    "driver_license_code95": {"driver_license", "driver_license_code95"},
}


def _extract_status(raw_status: Any) -> DocumentStatus | None:
    if isinstance(raw_status, DocumentStatus):
        return raw_status
    if raw_status is None:
        return None
    try:
        return DocumentStatus(str(raw_status))
    except ValueError:
        return None


def _iter_documents(documents: Sequence[Document] | Iterable[Any]) -> Iterable[Document]:
    return documents


def _doc_type_of(doc: Any) -> str:
    raw_type = getattr(doc, "doc_type", None)
    if raw_type is None and isinstance(doc, Mapping):
        raw_type = doc.get("doc_type")
    return normalize_doc_type(str(raw_type or ""))


def _last_check_decision(doc: Any, last_check_by_document_id: Mapping[str, Any] | None) -> str:
    if not last_check_by_document_id:
        return ""
    did = getattr(doc, "id", None)
    if did is None and isinstance(doc, Mapping):
        did = doc.get("id")
    if not did:
        return ""
    row = last_check_by_document_id.get(str(did))
    if row is None:
        return ""
    if isinstance(row, Mapping):
        return str(row.get("decision") or "").strip().lower()
    return str(getattr(row, "decision", "") or "").strip().lower()


def _status_is_ready(doc: Any) -> bool:
    status = _extract_status(getattr(doc, "status", None))
    if status is None and isinstance(doc, Mapping):
        status = _extract_status(doc.get("status"))
    return status in READY_ORDER_STATUSES


def _document_ready_for_handoff_gate(doc: Any, last_check_by_document_id: Mapping[str, Any] | None) -> bool:
    """Parity with owner_summary._effective_status — reviewer decision wins over stale row status."""
    decision = _last_check_decision(doc, last_check_by_document_id)
    if decision == "rejected":
        return False
    if decision == "approved":
        return True
    return _status_is_ready(doc)


def has_ready_document(
    documents: Sequence[Any],
    doc_type: str,
    last_check_by_document_id: Mapping[str, Any] | None = None,
) -> bool:
    canonical = normalize_doc_type(doc_type)
    if not canonical:
        return False
    acceptable = SATISFYING_TYPES.get(canonical, {canonical})
    for doc in _iter_documents(documents):
        if _doc_type_of(doc) not in acceptable:
            continue
        if _document_ready_for_handoff_gate(doc, last_check_by_document_id):
            return True
    return False


def base_required_types(checklist: Mapping[str, Any]) -> List[str]:
    required = []
    for raw in checklist.get("requiredTypes") or []:
        canonical = normalize_doc_type(str(raw))
        if not canonical:
            continue
        if canonical in ORDERABLE_CODES:
            continue
        required.append(canonical)
    return required


def missing_base_requirements(
    checklist: Mapping[str, Any],
    documents: Sequence[Any],
    last_check_by_document_id: Mapping[str, Any] | None = None,
) -> List[str]:
    missing: List[str] = []
    for doc_type in base_required_types(checklist):
        if not has_ready_document(documents, doc_type, last_check_by_document_id):
            missing.append(doc_type)
    return missing


def find_documents_by_type(documents: Sequence[Any], doc_type: str) -> List[Any]:
    canonical = normalize_doc_type(doc_type)
    if not canonical:
        return []
    return [doc for doc in _iter_documents(documents) if _doc_type_of(doc) == canonical]


def is_orderable(doc_type: str) -> bool:
    return normalize_doc_type(doc_type) in ORDERABLE_CODES


def default_order_date(provided: date | None = None) -> date:
    return provided or date.today()
