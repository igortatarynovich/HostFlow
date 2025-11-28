from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    code: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        raise ValidationError("DOC-005", f"Invalid date format: {value}")


def validate_date_range(issued_at: Optional[date], expires_at: Optional[date]) -> None:
    if issued_at and expires_at and expires_at < issued_at:
        raise ValidationError("DOC-003", "expires_at < issued_at")


def validate_meta(
    meta: Dict[str, Any],
    schema: Optional[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Validates meta payload against schema definition. Returns list of errors.
    Supports simple schema structure {"fields": { field_name: {type, required, regex, enum?...}}}
    """
    if not isinstance(schema, dict):
        return []
    fields = schema.get("fields")
    if not isinstance(fields, dict):
        # treat schema itself as field map (flat structure)
        fields = schema

    errors: List[Dict[str, str]] = []
    data = meta or {}

    for field_name, spec in fields.items():
        if not isinstance(spec, dict):
            continue

        value = data.get(field_name)
        required = bool(spec.get("required"))

        if required and (value is None or (isinstance(value, str) and not value.strip())):
            errors.append(
                {
                    "field": field_name,
                    "code": "required",
                    "message": "Field is required",
                }
            )
            continue

        if value is None:
            continue

        expected_type = spec.get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(
                {
                    "field": field_name,
                    "code": "type",
                    "message": "Expected string",
                }
            )
            continue

        if expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(
                {
                    "field": field_name,
                    "code": "type",
                    "message": "Expected number",
                }
            )
            continue

        if expected_type == "boolean" and not isinstance(value, bool):
            errors.append(
                {
                    "field": field_name,
                    "code": "type",
                    "message": "Expected boolean",
                }
            )
            continue

        if expected_type == "array":
            if not isinstance(value, list):
                errors.append(
                    {
                        "field": field_name,
                        "code": "type",
                        "message": "Expected array",
                    }
                )
                continue
            item_spec = spec.get("items")
            if isinstance(item_spec, dict):
                item_type = item_spec.get("type")
                for idx, item in enumerate(value):
                    if item_type == "string" and not isinstance(item, str):
                        errors.append(
                            {
                                "field": f"{field_name}[{idx}]",
                                "code": "type",
                                "message": "Expected string item",
                            }
                        )
                    elif item_type == "number" and not isinstance(item, (int, float)):
                        errors.append(
                            {
                                "field": f"{field_name}[{idx}]",
                                "code": "type",
                                "message": "Expected numeric item",
                            }
                        )

        if expected_type == "date":
            try:
                str_value = str(value)
                datetime.fromisoformat(str_value[:10])
            except Exception:
                errors.append(
                    {
                        "field": field_name,
                        "code": "format",
                        "message": "Expected ISO date (YYYY-MM-DD)",
                    }
                )
                continue

        regex = spec.get("regex")
        if regex and isinstance(value, str):
            if not re.fullmatch(regex, value):
                errors.append(
                    {
                        "field": field_name,
                        "code": "regex",
                        "message": f"Value does not match pattern {regex}",
                    }
                )

        enum_values = spec.get("enum")
        if isinstance(enum_values, list) and value not in enum_values:
            errors.append(
                {
                    "field": field_name,
                    "code": "enum",
                    "message": "Value not allowed",
                }
            )

    return errors
