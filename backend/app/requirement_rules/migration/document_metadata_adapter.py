"""Legacy document metadata → DocumentData migration adapter (PR 2B-4.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from backend.app.document_types.registry import normalize_input_doc_type
from backend.app.document_types.schema_registry import normalize_raw_to_document_data
from backend.app.requirement_rules.migration.iso_country import normalize_country_iso2

_CODE95_LEGACY_KEYS = (
    "code_95_valid_to",
    "code95_valid_to",
    "code95_expires_at",
    "code_95_expiry",
    "code95_expiry",
    "code95_valid_until",
    "code_95_valid_until",
)

_ISSUING_COUNTRY_KEYS = (
    "issuing_country",
    "country",
    "issuer_country",
    "document_country",
    "country_of_issue",
)

_DRIVER_LICENSE_TYPES = frozenset({"driver_license", "driver_licence", "drivers_license", "prawo_jazdy"})
_CODE95_TYPES = frozenset({"driver_qualification_card", "code95", "code_95", "qualification_card"})


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _merge_raw_sources(meta: dict[str, Any]) -> dict[str, Any]:
    merged = dict(meta or {})
    extracted = meta.get("extracted_fields") or meta.get("fields")
    if isinstance(extracted, dict):
        for key, value in extracted.items():
            merged.setdefault(key, value)
    nested = meta.get("document_data")
    if isinstance(nested, dict):
        for key, value in nested.items():
            merged.setdefault(key, value)
    return merged


def _first_present(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            value = raw[key]
            if isinstance(value, str) and not value.strip():
                continue
            return value
    return None


def _parse_date_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:10] if len(text) >= 10 else text


@dataclass(frozen=True)
class DocumentMetadataMigrationResult:
    document_data: dict[str, Any]
    issues: tuple[str, ...]
    changed: bool
    code95_validity_unresolved: bool


def migrate_legacy_document_metadata(
    *,
    stored_doc_type: str,
    meta: dict[str, Any],
    expire_date: Any = None,
    separate_code95_doc_expire_date: Any = None,
) -> DocumentMetadataMigrationResult:
    """Single adapter: legacy meta → canonical DocumentData with migration issues."""
    canonical = _norm(normalize_input_doc_type(stored_doc_type))
    raw = _merge_raw_sources(meta if isinstance(meta, dict) else {})
    issues: list[str] = []
    code95_unresolved = False

    document_data = normalize_raw_to_document_data(canonical, raw)
    changed = bool(document_data)

    # Issuing country — never infer from candidate citizenship.
    if not document_data.get("issuing_country"):
        country_raw = _first_present(raw, _ISSUING_COUNTRY_KEYS)
        iso2 = normalize_country_iso2(country_raw)
        if iso2:
            document_data["issuing_country"] = iso2
            changed = True

    # Code 95 validity for driver license and standalone qualification card.
    if canonical in _DRIVER_LICENSE_TYPES or canonical in _CODE95_TYPES:
        if not document_data.get("code_95_valid_to"):
            code95_raw = _first_present(raw, _CODE95_LEGACY_KEYS)
            if not code95_raw and canonical in _CODE95_TYPES:
                code95_raw = _parse_date_string(expire_date) or _parse_date_string(separate_code95_doc_expire_date)
            parsed = _parse_date_string(code95_raw)
            if parsed:
                document_data["code_95_valid_to"] = parsed
                changed = True
            elif canonical in _DRIVER_LICENSE_TYPES:
                categories = document_data.get("categories") or []
                needs_code95 = any(
                    str(cat).upper() in {"CE", "C1E", "DE"}
                    for cat in (categories if isinstance(categories, list) else [categories])
                )
                if needs_code95:
                    issues.append("code95_validity_unresolved")
                    code95_unresolved = True

    if canonical in _CODE95_TYPES and not document_data.get("expiry_date"):
        expiry = _parse_date_string(expire_date) or document_data.get("code_95_valid_to")
        if expiry:
            document_data["expiry_date"] = expiry
            changed = True

    return DocumentMetadataMigrationResult(
        document_data=document_data,
        issues=tuple(issues),
        changed=changed,
        code95_validity_unresolved=code95_unresolved,
    )


__all__ = ["DocumentMetadataMigrationResult", "migrate_legacy_document_metadata"]
