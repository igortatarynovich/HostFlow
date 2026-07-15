"""Driver CE DocumentTypeVersion schema bundle loader and validator (ADR-018 PR 2A)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

_SPECS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "specs" / "platform"
DRIVER_CE_SCHEMAS_PATH = _SPECS_ROOT / "document-type-schemas-driver-ce-v1.json"


class DocumentSchemaRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentTypeSchemaBundle:
    document_type_code: str
    version_code: str
    json_schema: dict[str, Any]
    expiry_field: Optional[str]
    validity_fields: dict[str, Optional[str]]
    evaluation_fields: tuple[str, ...]
    sensitivity: str
    sensitive_fields: tuple[str, ...]
    extraction_mapping: dict[str, tuple[str, ...]]
    conditional_required: tuple[dict[str, Any], ...]
    ui_labels: dict[str, dict[str, str]]
    process_generated: bool = False


def _norm(value: Optional[str]) -> str:
    return str(value or "").strip().lower().replace("-", "_")


@lru_cache(maxsize=1)
def load_driver_ce_schema_payload() -> dict[str, Any]:
    if not DRIVER_CE_SCHEMAS_PATH.is_file():
        raise DocumentSchemaRegistryError(f"Driver CE schema bundle missing: {DRIVER_CE_SCHEMAS_PATH}")
    with DRIVER_CE_SCHEMAS_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise DocumentSchemaRegistryError("Schema bundle root must be an object")
    return payload


@lru_cache(maxsize=1)
def driver_ce_schema_bundle_version() -> str:
    return str(load_driver_ce_schema_payload().get("schema_bundle_version") or "unknown")


@lru_cache(maxsize=1)
def driver_ce_schema_bundles() -> dict[str, DocumentTypeSchemaBundle]:
    payload = load_driver_ce_schema_payload()
    raw_types = payload.get("document_types")
    if not isinstance(raw_types, dict):
        raise DocumentSchemaRegistryError("Schema bundle must contain document_types{}")

    bundles: dict[str, DocumentTypeSchemaBundle] = {}
    for code, raw in raw_types.items():
        if not isinstance(raw, dict):
            raise DocumentSchemaRegistryError(f"Schema for {code} must be an object")
        canonical = _norm(code)
        schema = raw.get("json_schema")
        if not isinstance(schema, dict):
            raise DocumentSchemaRegistryError(f"Schema for {canonical} missing json_schema")
        mapping_raw = raw.get("extraction_mapping") or {}
        mapping: dict[str, tuple[str, ...]] = {}
        if isinstance(mapping_raw, dict):
            for field, aliases in mapping_raw.items():
                if isinstance(aliases, list):
                    mapping[_norm(field)] = tuple(_norm(x) for x in aliases if _norm(x))
        validity = raw.get("validity_fields") if isinstance(raw.get("validity_fields"), dict) else {}
        cond = raw.get("conditional_required") or []
        bundles[canonical] = DocumentTypeSchemaBundle(
            document_type_code=canonical,
            version_code=str(raw.get("version_code") or "v1"),
            json_schema=schema,
            expiry_field=_norm(raw["expiry_field"]) if raw.get("expiry_field") else None,
            validity_fields={
                "valid_from": _norm(validity.get("valid_from")) if validity.get("valid_from") else None,
                "valid_to": _norm(validity.get("valid_to")) if validity.get("valid_to") else None,
            },
            evaluation_fields=tuple(str(x) for x in (raw.get("evaluation_fields") or [])),
            sensitivity=str(raw.get("sensitivity") or "medium"),
            sensitive_fields=tuple(str(x) for x in (raw.get("sensitive_fields") or [])),
            extraction_mapping=mapping,
            conditional_required=tuple(dict(x) for x in cond if isinstance(x, dict)),
            ui_labels=dict(raw.get("ui_labels") or {}),
            process_generated=bool(raw.get("process_generated")),
        )
    return bundles


def get_driver_ce_schema_bundle(document_type_code: str) -> Optional[DocumentTypeSchemaBundle]:
    return driver_ce_schema_bundles().get(_norm(document_type_code))


def validate_document_data(
    document_type_code: str,
    data: dict[str, Any],
    *,
    evaluation_date: Optional[str] = None,
) -> tuple[bool, list[str]]:
    """Validate DocumentData against versioned schema. Returns (ok, errors)."""
    bundle = get_driver_ce_schema_bundle(document_type_code)
    if bundle is None:
        return False, [f"unknown_document_type:{document_type_code}"]

    validator = Draft202012Validator(bundle.json_schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(data or {}), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "$"
        errors.append(f"{path}: {err.message}")

    for rule in bundle.conditional_required:
        when = rule.get("when") if isinstance(rule.get("when"), dict) else {}
        field = _norm(when.get("field"))
        contains_any = when.get("contains_any") or []
        if field and contains_any:
            values = data.get(field) if isinstance(data, dict) else None
            if isinstance(values, list):
                normalized = {str(v).upper() for v in values}
                if normalized.intersection({str(v).upper() for v in contains_any}):
                    for req_field in rule.get("required_fields") or []:
                        if not (data or {}).get(req_field):
                            errors.append(f"{req_field}: conditionally required")

    return len(errors) == 0, errors


def normalize_raw_to_document_data(
    document_type_code: str,
    raw: dict[str, Any],
) -> dict[str, Any]:
    """Hub-boundary adapter: map legacy meta/extraction keys to canonical DocumentData fields."""
    bundle = get_driver_ce_schema_bundle(document_type_code)
    if bundle is None or not isinstance(raw, dict):
        return dict(raw or {})

    out: dict[str, Any] = {}
    for canonical_field, aliases in bundle.extraction_mapping.items():
        for alias in (canonical_field, *aliases):
            if alias in raw and raw[alias] is not None:
                value = raw[alias]
                if isinstance(value, str) and not value.strip():
                    continue
                out[canonical_field] = value
                break

    if "categories" in out:
        out["categories"] = normalize_driver_categories(out["categories"])
    if "issuing_country" in out:
        normalized_country = _normalize_document_country(out["issuing_country"])
        if normalized_country:
            out["issuing_country"] = normalized_country
    if "nationality" in out:
        normalized_nationality = _normalize_document_country(out["nationality"])
        if normalized_nationality:
            out["nationality"] = normalized_nationality

    return out


_CATEGORY_LABEL_MAP = {
    "c+e": "CE",
    "c1+e": "C1E",
    "d+e": "DE",
    "b": "B",
    "c": "C",
    "ce": "CE",
    "c1": "C1",
    "c1e": "C1E",
    "d": "D",
    "de": "DE",
}


_VALID_DRIVER_CATEGORIES = frozenset({"B", "C", "CE", "C1", "C1E", "D", "DE"})


def normalize_driver_categories(value: Any) -> list[str]:
    """Normalize legacy driver category strings/arrays to canonical enum values."""
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        text = value.replace(";", ",").replace("/", ",")
        items = [part.strip() for part in text.split(",") if part.strip()]
    else:
        items = [value]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        token = str(item).strip().upper().replace(" ", "")
        if "+" in token:
            parts = [part for part in token.split("+") if part]
            if len(parts) == 2:
                token = f"{parts[0]}{parts[1]}"
        mapped = _CATEGORY_LABEL_MAP.get(token.lower(), token)
        if mapped in _VALID_DRIVER_CATEGORIES and mapped not in seen:
            seen.add(mapped)
            normalized.append(mapped)
    return normalized


def _normalize_document_country(value: Any) -> Optional[str]:
    from backend.app.reference.iso_country import normalize_country_iso2

    return normalize_country_iso2(value)


__all__ = [
    "DRIVER_CE_SCHEMAS_PATH",
    "DocumentSchemaRegistryError",
    "DocumentTypeSchemaBundle",
    "driver_ce_schema_bundle_version",
    "driver_ce_schema_bundles",
    "get_driver_ce_schema_bundle",
    "normalize_driver_categories",
    "normalize_raw_to_document_data",
    "validate_document_data",
]
