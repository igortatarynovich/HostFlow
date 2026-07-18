"""Forms Sprint 4 — submission validation against frozen field schema.

Pure functions. No dynamic code execution. No Builder.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.forms_platform.errors import FormsAdapterError
from backend.app.forms_platform.schema import (
    FIELD_SCHEMA_CONTRACT,
    LEGACY_PAYLOAD_KEYS,
    extract_field_schema,
)


class FormsValidationError(FormsAdapterError):
    code = "forms_submission_validation_failed"
    http_status = 422
    default_message = "Submission failed field schema validation"


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{5,}$")


def normalize_submission_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize intake payload to {field_id: value} flat map."""
    raw = dict(payload or {})
    if isinstance(raw.get("values"), dict):
        values = dict(raw["values"])
    else:
        values = {
            str(k): v
            for k, v in raw.items()
            if str(k) not in LEGACY_PAYLOAD_KEYS or str(k) == "values"
        }
        # Prefer presentation_values_v1 when present
        pv = raw.get("presentation_values_v1")
        if isinstance(pv, dict):
            values = {**values, **{str(k): v for k, v in pv.items()}}
    return {str(k).strip(): v for k, v in values.items() if str(k).strip()}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _type_error(field_id: str, field_type: str, value: Any) -> dict[str, Any] | None:
    if _is_empty(value):
        return None
    t = str(field_type or "text")
    if t in {"text", "textarea", "string", "reference_code", "enum", "url", "file"}:
        if not isinstance(value, (str, int, float, bool)):
            return {
                "code": "forms_field_type_invalid",
                "field_id": field_id,
                "message": f"Field {field_id} expects scalar text-compatible value",
                "expected_type": t,
            }
        return None
    if t == "email":
        if not isinstance(value, str) or not _EMAIL_RE.match(value.strip()):
            return {
                "code": "forms_field_type_invalid",
                "field_id": field_id,
                "message": f"Field {field_id} expects email",
                "expected_type": t,
            }
        return None
    if t in {"phone", "phone_e164"}:
        if not isinstance(value, str) or not _PHONE_RE.match(value.strip()):
            return {
                "code": "forms_field_type_invalid",
                "field_id": field_id,
                "message": f"Field {field_id} expects phone",
                "expected_type": t,
            }
        return None
    if t == "boolean":
        if not isinstance(value, bool) and str(value).lower() not in {"true", "false", "0", "1"}:
            return {
                "code": "forms_field_type_invalid",
                "field_id": field_id,
                "message": f"Field {field_id} expects boolean",
                "expected_type": t,
            }
        return None
    if t in {"integer", "number"}:
        try:
            if t == "integer":
                int(value)
            else:
                float(value)
        except (TypeError, ValueError):
            return {
                "code": "forms_field_type_invalid",
                "field_id": field_id,
                "message": f"Field {field_id} expects {t}",
                "expected_type": t,
            }
        return None
    if t in {"date", "datetime"}:
        if not isinstance(value, str) or len(value.strip()) < 4:
            return {
                "code": "forms_field_type_invalid",
                "field_id": field_id,
                "message": f"Field {field_id} expects {t} string",
                "expected_type": t,
            }
        return None
    if t == "json":
        if not isinstance(value, (dict, list)):
            return {
                "code": "forms_field_type_invalid",
                "field_id": field_id,
                "message": f"Field {field_id} expects json object/array",
                "expected_type": t,
            }
        return None
    return None


def validate_submission(
    schema: dict[str, Any] | None,
    payload: dict[str, Any] | None,
    *,
    published_version: int | None = None,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    """Validate payload against frozen forms.field_schema.v1.

    Pre-schema snapshots (schema is None / missing contract): compat_mode=pre_schema,
    no unknown-field rejection (legacy).
    """
    normalized = normalize_submission_payload(payload)
    if not schema or schema.get("schema_contract") != FIELD_SCHEMA_CONTRACT:
        result = {
            "ok": True,
            "compat_mode": "pre_schema",
            "published_version": published_version,
            "normalized_values": normalized,
            "errors": [],
            "schema_contract": None,
        }
        return result

    fields = schema.get("fields") if isinstance(schema.get("fields"), list) else []
    by_id = {
        str(f.get("id")): f
        for f in fields
        if isinstance(f, dict) and str(f.get("id") or "").strip()
    }
    allow = set(by_id.keys())
    compat = schema.get("compat") if isinstance(schema.get("compat"), dict) else {}
    unknown_mode = str(compat.get("unknown_fields") or "reject")
    missing_mode = str(compat.get("missing_required") or "reject")

    errors: list[dict[str, Any]] = []

    unknown = sorted(k for k in normalized.keys() if k not in allow)
    if unknown and unknown_mode == "reject":
        for field_id in unknown:
            errors.append(
                {
                    "code": "forms_unknown_field",
                    "field_id": field_id,
                    "message": f"Unknown field not in published schema: {field_id}",
                }
            )

    for field_id, spec in by_id.items():
        required = bool(spec.get("required"))
        value = normalized.get(field_id)
        if required and missing_mode == "reject" and _is_empty(value):
            errors.append(
                {
                    "code": "forms_required_field_missing",
                    "field_id": field_id,
                    "message": f"Required field missing: {field_id}",
                }
            )
            continue
        type_err = _type_error(field_id, str(spec.get("type") or "text"), value)
        if type_err is not None:
            errors.append(type_err)

    # Drop unknown keys from normalized output when rejecting unknowns
    if unknown_mode == "reject":
        normalized_out = {k: v for k, v in normalized.items() if k in allow}
    else:
        normalized_out = dict(normalized)

    result = {
        "ok": len(errors) == 0,
        "compat_mode": "field_schema_v1",
        "published_version": published_version,
        "normalized_values": normalized_out,
        "errors": errors,
        "schema_contract": FIELD_SCHEMA_CONTRACT,
    }
    if raise_on_error and not result["ok"]:
        raise FormsValidationError(
            details={"errors": errors, "published_version": published_version}
        )
    return result


def validate_submission_against_publication(
    publication_or_snapshot: dict[str, Any],
    payload: dict[str, Any] | None,
    *,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    schema = extract_field_schema(publication_or_snapshot)
    version = publication_or_snapshot.get("published_version")
    if version is None and isinstance(publication_or_snapshot.get("snapshot"), dict):
        version = publication_or_snapshot["snapshot"].get("published_version")
    return validate_submission(
        schema,
        payload,
        published_version=int(version) if version is not None else None,
        raise_on_error=raise_on_error,
    )
