"""Forms Sprint 4 — canonical field schema contract (frozen into publication versions).

No visual Builder. Schema is data, not executable code.
"""

from __future__ import annotations

from typing import Any

FIELD_SCHEMA_CONTRACT = "forms.field_schema.v1"

ALLOWED_FIELD_TYPES = frozenset(
    {
        "text",
        "string",
        "email",
        "phone",
        "phone_e164",
        "boolean",
        "integer",
        "number",
        "date",
        "datetime",
        "reference_code",
        "enum",
        "json",
        "file",
        "textarea",
        "url",
    }
)

LEGACY_PAYLOAD_KEYS = frozenset({"contacts", "personal", "experience", "agreements", "values"})


def normalize_field_type(raw: Any) -> str:
    t = str(raw or "text").strip().lower() or "text"
    if t == "string":
        return "text"
    return t if t in ALLOWED_FIELD_TYPES else "text"


def build_field_schema_v1(
    *,
    fields: list[dict[str, Any]],
    entity_profile_code: str | None = None,
    presentation_code: str | None = None,
    unknown_fields: str = "reject",
    missing_required: str = "reject",
) -> dict[str, Any]:
    """Build immutable field schema document for a publication version."""
    normalized_fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in fields or []:
        if not isinstance(raw, dict):
            continue
        field_id = str(raw.get("id") or raw.get("qualified_code") or "").strip()
        if not field_id or field_id in seen:
            continue
        level = str(raw.get("intake_level") or "optional").strip().lower()
        if level == "hidden":
            continue
        if isinstance(raw.get("required"), bool):
            required = bool(raw["required"])
        else:
            required = level == "required"
        validation = raw.get("validation") if isinstance(raw.get("validation"), dict) else {}
        normalized_fields.append(
            {
                "id": field_id,
                "type": normalize_field_type(raw.get("type") or raw.get("field_type")),
                "required": bool(required),
                "validation": dict(validation),
            }
        )
        seen.add(field_id)

    return {
        "schema_contract": FIELD_SCHEMA_CONTRACT,
        "entity_profile_code": entity_profile_code,
        "presentation_code": presentation_code,
        "fields": normalized_fields,
        "compat": {
            "unknown_fields": unknown_fields,
            "missing_required": missing_required,
            "extra_legacy_keys_allowed": sorted(LEGACY_PAYLOAD_KEYS - {"values"}),
            "policy": (
                "Snapshots without schema_contract use pre_schema compat "
                "(live required checks only). Snapshots with forms.field_schema.v1 "
                "enforce unknown rejection + required + type checks against frozen fields."
            ),
        },
    }


def field_schema_from_presentation_runtime(
    runtime: dict[str, Any] | None,
) -> dict[str, Any]:
    """Map form_presentation_runtime_v1 → forms.field_schema.v1."""
    runtime = runtime or {}
    fields_in = runtime.get("fields") if isinstance(runtime.get("fields"), list) else []
    mapped: list[dict[str, Any]] = []
    for row in fields_in:
        if not isinstance(row, dict):
            continue
        mapped.append(
            {
                "id": row.get("qualified_code"),
                "type": row.get("field_type") or "text",
                "intake_level": row.get("intake_level") or "optional",
                "validation": {},
            }
        )
    return build_field_schema_v1(
        fields=mapped,
        entity_profile_code=runtime.get("entity_profile_code"),
        presentation_code=runtime.get("presentation_code"),
    )


def extract_field_schema(snapshot_or_publication: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return frozen field schema from publication/snapshot, or None (pre-schema)."""
    src = snapshot_or_publication or {}
    schema = src.get("field_schema")
    if isinstance(schema, dict) and schema.get("schema_contract") == FIELD_SCHEMA_CONTRACT:
        return schema
    # Also allow schema nested under snapshot key
    snap = src.get("snapshot")
    if isinstance(snap, dict):
        nested = snap.get("field_schema")
        if isinstance(nested, dict) and nested.get("schema_contract") == FIELD_SCHEMA_CONTRACT:
            return nested
    return None
