"""Document extraction context for requirements workspace (A3-C)."""

from __future__ import annotations

from typing import Any

from backend.app.services.document_catalog import DOCUMENT_TYPE_ALIASES, DOCUMENT_TYPE_DEFAULTS, normalize_doc_type

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "number": ("number", "passport_number", "license_number", "document_number"),
    "expires_at": ("expires_at", "expire_date", "expiry_date"),
    "issued_at": ("issued_at", "issue_date"),
    "categories": ("categories", "license_categories"),
    "country": ("country", "nationality"),
}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _canonical_doc_type(raw: str) -> str:
    normalized = normalize_doc_type(raw)
    return DOCUMENT_TYPE_ALIASES.get(normalized, normalized)


def _merged_field_sources(snapshot: dict[str, Any]) -> dict[str, Any]:
    meta = snapshot.get("meta") if isinstance(snapshot.get("meta"), dict) else {}
    extracted = snapshot.get("extracted_fields")
    if not isinstance(extracted, dict):
        extracted = meta.get("extracted_fields") or meta.get("fields") or {}
    if not isinstance(extracted, dict):
        extracted = {}
    sources: dict[str, Any] = {**meta, **extracted}
    expires = snapshot.get("expires_on") or snapshot.get("expire_date")
    if expires and not sources.get("expires_at"):
        sources["expires_at"] = expires
    return sources


def _field_present(sources: dict[str, Any], field_code: str) -> bool:
    keys = _FIELD_ALIASES.get(field_code, (field_code,))
    for key in keys:
        value = sources.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            if value:
                return True
            continue
        if str(value).strip():
            return True
    return False


def required_extraction_fields_for_type(doc_type: str) -> list[str]:
    canonical = _canonical_doc_type(doc_type)
    defaults = DOCUMENT_TYPE_DEFAULTS.get(canonical)
    if defaults is None:
        return []
    return list(defaults.required_meta)


def extracted_fields_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    sources = _merged_field_sources(snapshot)
    doc_type = _norm(snapshot.get("document_type_code") or snapshot.get("type"))
    required = required_extraction_fields_for_type(doc_type)
    extracted: dict[str, Any] = {}
    for field_code in required:
        keys = _FIELD_ALIASES.get(field_code, (field_code,))
        for key in keys:
            if key in sources and sources[key] is not None:
                value = sources[key]
                if isinstance(value, (list, tuple, set)) and not value:
                    continue
                if not isinstance(value, (list, tuple, set)) and not str(value).strip():
                    continue
                extracted[field_code] = value
                break
    for key, value in sources.items():
        if key not in extracted and _norm(key) in {_norm(x) for x in required}:
            extracted[key] = value
    return extracted


def missing_extraction_fields(snapshot: dict[str, Any]) -> list[str]:
    doc_type = _norm(snapshot.get("document_type_code") or snapshot.get("type"))
    required = required_extraction_fields_for_type(doc_type)
    if not required:
        return []
    sources = _merged_field_sources(snapshot)
    return [field_code for field_code in required if not _field_present(sources, field_code)]


def enrich_document_snapshot_for_checklist(snapshot: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(snapshot)
    doc_type = str(enriched.get("document_type_code") or enriched.get("type") or "")
    required = required_extraction_fields_for_type(doc_type)
    extracted = extracted_fields_from_snapshot(enriched)
    missing = missing_extraction_fields(enriched)
    enriched["extracted_fields"] = extracted
    enriched["required_extraction_fields"] = required
    enriched["missing_extraction_fields"] = missing
    return enriched


def extraction_blockers_for_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for doc in documents or []:
        if not isinstance(doc, dict):
            continue
        missing = doc.get("missing_extraction_fields")
        if not isinstance(missing, list):
            missing = missing_extraction_fields(doc)
        if not missing:
            continue
        doc_type = _norm(doc.get("document_type_code") or doc.get("type"))
        doc_id = str(doc.get("document_id") or doc.get("id") or "").strip() or None
        for field_code in missing:
            blockers.append(
                {
                    "code": "document_extraction_field_missing",
                    "message": f"Missing extraction field {field_code} on {doc_type or 'document'}",
                    "document_type_code": doc_type or None,
                    "document_id": doc_id,
                    "field_code": field_code,
                    "qualified_code": f"document.{doc_type}.{field_code}" if doc_type else field_code,
                    "source_layer": "document_extraction",
                    "layer": "document_extraction",
                }
            )
    return blockers
