"""Pure utility primitives shared across the communications package.

Extracted from ``communications/__init__.py`` (Phase 1 god-module split).
These helpers MUST stay free of intra-package dependencies (only stdlib +
third-party libs allowed) so any other helper module can import from here
without risking circular imports.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

__all__ = [
    "_now_utc",
    "_as_dict",
    "_as_list",
    "_coerce_datetime",
    "_clamp_db_str",
    "_deep_merge_dict",
    "_json_dict",
    "_normalize_email_value",
    "_digits_only",
    "_looks_like_phone",
    "_is_six_digit_code",
]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(value: Any) -> Dict[str, Any]:
    return {**value} if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            normalized = text.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _clamp_db_str(value: Any, max_len: int) -> str | None:
    """VARCHAR-safe slice for IMAP/OAuth poll payloads (long RFC822 From/To, Message-IDs)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if len(s) <= max_len:
        return s
    return s[:max_len]


def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = _as_dict(base)
    for key, value in _as_dict(patch).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dict(_as_dict(out.get(key)), _as_dict(value))
        else:
            out[key] = value
    return out


def _json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return {**value}
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _normalize_email_value(value: str | None) -> str | None:
    raw = str(value or "").strip().lower()
    return raw if raw and "@" in raw else None


def _digits_only(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _looks_like_phone(value: str | None) -> bool:
    d = _digits_only(value)
    return len(d) >= 8


def _is_six_digit_code(value: str | None) -> bool:
    return bool(re.fullmatch(r"\d{6}", str(value or "").strip()))
