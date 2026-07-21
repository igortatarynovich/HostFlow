"""Typed variable checks for the pure renderer (no I/O)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from backend.app.communications.templates.renderer.types import VARIABLE_TYPES

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{6,31}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BOOL_TRUE = frozenset({"true", "1", "yes", "y", "on"})
_BOOL_FALSE = frozenset({"false", "0", "no", "n", "off"})


def normalize_var_type(raw: str) -> str:
    t = str(raw or "string").strip().lower() or "string"
    if t == "bool":
        return "boolean"
    return t


def is_known_type(var_type: str) -> bool:
    return normalize_var_type(var_type) in VARIABLE_TYPES or var_type in VARIABLE_TYPES


def check_value_type(
    *,
    var_type: str,
    value: Any,
    enum_values: tuple[str, ...] = (),
) -> str | None:
    """Return error message if value does not match type; None if OK."""
    t = normalize_var_type(var_type)
    if t not in VARIABLE_TYPES and t != "boolean":
        return f"Unknown variable type: {var_type}"

    if value is None:
        return "value is null"

    if t in {"string", "text", "markdown", "html"}:
        if not isinstance(value, str):
            return f"expected string, got {type(value).__name__}"
        return None

    if t == "email":
        s = str(value).strip()
        if not _EMAIL_RE.match(s):
            return "invalid email"
        return None

    if t == "phone":
        s = str(value).strip()
        if not _PHONE_RE.match(s):
            return "invalid phone"
        return None

    if t == "url":
        s = str(value).strip()
        parsed = urlparse(s)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "invalid url (http/https required)"
        return None

    if t == "date":
        if isinstance(value, date) and not isinstance(value, datetime):
            return None
        s = str(value).strip()
        if not _DATE_RE.match(s):
            return "invalid date (expected YYYY-MM-DD)"
        try:
            date.fromisoformat(s)
        except ValueError:
            return "invalid date (expected YYYY-MM-DD)"
        return None

    if t == "datetime":
        if isinstance(value, datetime):
            return None
        s = str(value).strip()
        try:
            # Accept trailing Z
            datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return "invalid datetime (expected ISO-8601)"
        return None

    if t == "currency":
        if isinstance(value, (int, float, Decimal)):
            return None
        s = str(value).strip().replace(",", "")
        try:
            Decimal(s)
        except (InvalidOperation, ValueError):
            return "invalid currency amount"
        return None

    if t in {"boolean", "bool"}:
        if isinstance(value, bool):
            return None
        s = str(value).strip().lower()
        if s in _BOOL_TRUE or s in _BOOL_FALSE:
            return None
        return "invalid boolean"

    if t == "number":
        if isinstance(value, bool):
            return "invalid number"
        if isinstance(value, (int, float, Decimal)):
            return None
        s = str(value).strip()
        try:
            float(s)
        except ValueError:
            return "invalid number"
        return None

    if t == "enum":
        s = str(value)
        allowed = tuple(str(x) for x in enum_values)
        if not allowed:
            return "enum has no allowed values"
        if s not in allowed:
            return f"value not in enum {allowed}"
        return None

    return None


def coerce_for_render(*, var_type: str, value: Any) -> str:
    """Deterministic string coercion for substitution (after type check passed)."""
    t = normalize_var_type(var_type)
    if value is None:
        return ""
    if t in {"boolean", "bool"}:
        if isinstance(value, bool):
            return "true" if value else "false"
        s = str(value).strip().lower()
        if s in _BOOL_TRUE:
            return "true"
        if s in _BOOL_FALSE:
            return "false"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)
