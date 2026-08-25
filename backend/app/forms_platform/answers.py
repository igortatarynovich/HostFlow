"""Forms Sprint 5 — normalized answer contract.

Stable answers by field_id. Raw vs normalized. No domain mapping. No Builder.
Hand-off shape for Shared Intake only.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from backend.app.forms_platform.schema import FIELD_SCHEMA_CONTRACT

ANSWER_CONTRACT = "forms.normalized_answers.v1"

# Stable i18n keys for validation errors (message_key contract).
MESSAGE_KEYS = {
    "forms_unknown_field": "forms.validation.unknown_field",
    "forms_required_field_missing": "forms.validation.required_field_missing",
    "forms_field_type_invalid": "forms.validation.field_type_invalid",
    "forms_submission_validation_failed": "forms.validation.submission_failed",
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_DIGITS_RE = re.compile(r"[^\d+]")
_WS_RE = re.compile(r"\s+")


def validation_error(
    *,
    code: str,
    field_id: str | None = None,
    message: str,
    expected_type: str | None = None,
) -> dict[str, Any]:
    err: dict[str, Any] = {
        "field_id": field_id,
        "code": code,
        "message_key": MESSAGE_KEYS.get(code, "forms.validation.generic"),
        "message": message,
    }
    if expected_type is not None:
        err["expected_type"] = expected_type
    return err


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def normalize_string(value: Any) -> str:
    text = str(value).strip()
    return _WS_RE.sub(" ", text)


def normalize_email(value: Any) -> str:
    return normalize_string(value).lower()


def normalize_phone(value: Any) -> str:
    raw = str(value).strip()
    # Keep leading +, drop other non-digits.
    if raw.startswith("+"):
        return "+" + re.sub(r"\D", "", raw[1:])
    return re.sub(r"\D", "", raw)


def normalize_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"true", "1", "yes", "y", "on"}:
        return True
    if s in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError("not a boolean")


def normalize_integer(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("bool is not integer")
    return int(value)


def normalize_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("bool is not number")
    return float(value)


def normalize_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = normalize_string(value)
    # Accept YYYY-MM-DD or datetime prefix.
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        date.fromisoformat(text[:10])
        return text[:10]
    raise ValueError("not an ISO date")


def canonicalize_value(field_type: str, value: Any) -> Any:
    """Canonical normalization for a single field value. Raises ValueError on failure."""
    if _is_empty(value):
        return None
    t = str(field_type or "text")
    if t in {"text", "textarea", "string", "reference_code", "enum", "url", "file"}:
        return normalize_string(value)
    if t == "email":
        out = normalize_email(value)
        if not _EMAIL_RE.match(out):
            raise ValueError("invalid email")
        return out
    if t in {"phone", "phone_e164"}:
        out = normalize_phone(value)
        if len(re.sub(r"\D", "", out)) < 6:
            raise ValueError("invalid phone")
        return out
    if t == "boolean":
        return normalize_boolean(value)
    if t == "integer":
        return normalize_integer(value)
    if t == "number":
        return normalize_number(value)
    if t in {"date", "datetime"}:
        return normalize_date(value)
    if t == "json":
        if not isinstance(value, (dict, list)):
            raise ValueError("invalid json")
        return value
    return normalize_string(value)


def build_normalized_answers(
    *,
    schema: dict[str, Any] | None,
    raw_values: dict[str, Any],
    published_version: int | None = None,
    form_id: str | None = None,
    schema_contract: str | None = None,
) -> dict[str, Any]:
    """Build forms.normalized_answers.v1 from raw flat field map + optional schema.

    Unknown fields are rejected **after** extracting the flat map (not before).
    No domain/entity mapping — Forms only normalizes typed answers.
    """
    raw = {str(k).strip(): v for k, v in dict(raw_values or {}).items() if str(k).strip()}
    errors: list[dict[str, Any]] = []
    normalized: dict[str, Any] = {}

    has_schema = bool(schema and schema.get("schema_contract") == FIELD_SCHEMA_CONTRACT)
    if not has_schema:
        # Pre-schema: pass-through string trim only; keep all keys.
        for field_id, value in raw.items():
            if _is_empty(value):
                continue
            try:
                normalized[field_id] = normalize_string(value) if not isinstance(value, (dict, list, bool, int, float)) else value
            except Exception:
                normalized[field_id] = value
        answer = {
            "answer_contract": ANSWER_CONTRACT,
            "schema_contract": None,
            "compat_mode": "pre_schema",
            "published_version": published_version,
            "form_id": form_id,
            "raw_values": raw,
            "normalized_values": normalized,
            "errors": [],
            "ok": True,
        }
        answer["intake_handoff"] = _intake_handoff(answer)
        return answer

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

    # Unknown fields — after flat extraction / before accepting into normalized.
    unknown = sorted(k for k in raw.keys() if k not in allow)
    if unknown and unknown_mode == "reject":
        for field_id in unknown:
            errors.append(
                validation_error(
                    code="forms_unknown_field",
                    field_id=field_id,
                    message=f"Unknown field not in published schema: {field_id}",
                )
            )

    for field_id, spec in by_id.items():
        required = bool(spec.get("required"))
        raw_val = raw.get(field_id)
        if required and missing_mode == "reject" and _is_empty(raw_val):
            errors.append(
                validation_error(
                    code="forms_required_field_missing",
                    field_id=field_id,
                    message=f"Required field missing: {field_id}",
                )
            )
            continue
        if _is_empty(raw_val):
            continue
        field_type = str(spec.get("type") or "text")
        try:
            normalized[field_id] = canonicalize_value(field_type, raw_val)
        except (TypeError, ValueError):
            errors.append(
                validation_error(
                    code="forms_field_type_invalid",
                    field_id=field_id,
                    message=f"Field {field_id} failed {field_type} normalization",
                    expected_type=field_type,
                )
            )

    answer = {
        "answer_contract": ANSWER_CONTRACT,
        "schema_contract": schema_contract or FIELD_SCHEMA_CONTRACT,
        "compat_mode": "field_schema_v1",
        "published_version": published_version,
        "form_id": form_id,
        "raw_values": raw,
        "normalized_values": normalized,
        "errors": errors,
        "ok": len(errors) == 0,
    }
    answer["intake_handoff"] = _intake_handoff(answer)
    return answer


def _intake_handoff(answer: dict[str, Any]) -> dict[str, Any]:
    """Payload fragment for Shared Intake — no domain mapping."""
    return {
        "presentation_values_v1": dict(answer.get("normalized_values") or {}),
        "forms_answer_contract_v1": {
            "answer_contract": ANSWER_CONTRACT,
            "schema_contract": answer.get("schema_contract"),
            "published_version": answer.get("published_version"),
            "form_id": answer.get("form_id"),
            "ok": answer.get("ok"),
        },
        # Raw retained for audit; Intake must prefer presentation_values_v1.
        "forms_raw_values_v1": dict(answer.get("raw_values") or {}),
    }
