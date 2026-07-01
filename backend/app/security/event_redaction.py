"""Redaction for security event ``extra`` (Phase 2 spike)."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

_URLISH_RE = re.compile(r"https?://", re.IGNORECASE)
_SENSITIVE_URL_MARKERS = (
    "signature=",
    "x-amz-",
    "x-goog-",
    "token=",
    "access_token=",
    "id_token=",
)

# Keys removed anywhere in extra (case-insensitive match on leaf keys).
REDACTED_KEY_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "cookie",
        "set-cookie",
        "api_key",
        "apikey",
        "private_key",
        "refresh_token",
        "access_token",
        "id_token",
        "bearer",
        "ssn",
        "passport",
        "iban",
        "credit_card",
    }
)

# Whole key names (lowercase) always stripped from extra.
FORBIDDEN_EXACT_KEYS: frozenset[str] = frozenset(
    {
        "raw_body",
        "body",
        "payload",
        "email",
        "phone",
        "msisdn",
        "tel",
        "address",
        "notes",
        "content",
        "document_bytes",
        # Never ship raw URLs / tokens / human filenames in security event extra.
        "url",
        "signed_url",
        "download_url",
        "presigned_url",
        "filename",
        # Export / archive leaks (paths and row payloads must never appear in security extra).
        "archive_path",
        "export_path",
        "rows",
        "records",
        "attachment_filename",
        # Retrieval / AI / search leaks (never raw prompt, query, context, vectors).
        "prompt",
        "raw_prompt",
        "system_prompt",
        "user_prompt",
        "raw_query",
        "search_query",
        "query_text",
        "user_query",
        "raw_context",
        "prompt_context",
        "retrieval_context",
        "assembled_context",
        "conversation_context",
        "embedding",
        "embeddings",
        "vector",
        "vectors",
        "document_text",
        "chunk_text",
        "chunks",
        # Generic names that must never carry raw retrieval payload in security ``extra``.
        "context",
        "query",
    }
)

_MAX_EXTRA_JSON_BYTES_DEFAULT = 8192


def _is_redacted_key(key: str) -> bool:
    lk = (key or "").strip().lower()
    if lk in FORBIDDEN_EXACT_KEYS:
        return True
    return any(s in lk for s in REDACTED_KEY_SUBSTRINGS)


def _scrub_value(value: Any, depth: int) -> Any:
    if depth > 8:
        return "[TRUNCATED_DEPTH]"
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in value.items():
            ks = str(k)
            if _is_redacted_key(ks):
                out[ks] = "[REDACTED]"
            else:
                out[ks] = _scrub_value(v, depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_scrub_value(v, depth + 1) for v in value[:50]] + (
            ["[TRUNCATED_LIST]"] if len(value) > 50 else []
        )
    if isinstance(value, (str, bytes)):
        if isinstance(value, bytes):
            return "[BINARY_REDACTED]"
        if len(value) > 512:
            return value[:256] + "…[TRUNCATED]"
        if _URLISH_RE.search(value) and any(m in value.lower() for m in _SENSITIVE_URL_MARKERS):
            return "[REDACTED_SENSITIVE_VALUE]"
        return value
    return value


def apply_extra_allowlist(extra: dict[str, Any], allowlist: frozenset[str] | None) -> dict[str, Any]:
    if not allowlist:
        return dict(extra)
    return {k: v for k, v in extra.items() if k in allowlist}


def redact_and_size_extra(
    extra: Mapping[str, Any] | None,
    *,
    allowlist: frozenset[str] | None = None,
    max_json_bytes: int = _MAX_EXTRA_JSON_BYTES_DEFAULT,
) -> dict[str, Any]:
    """Return scrubbed ``extra`` dict, enforce allowlist and max serialized size."""
    base: dict[str, Any] = dict(extra or {})
    base = apply_extra_allowlist(base, allowlist)
    scrubbed = _scrub_value(base, 0)
    if not isinstance(scrubbed, dict):
        scrubbed = {"_value": scrubbed}
    raw = json.dumps(scrubbed, default=str, separators=(",", ":")).encode("utf-8")
    if len(raw) <= max_json_bytes:
        return scrubbed
    return {
        "_truncated": True,
        "max_bytes": max_json_bytes,
        "approx_original_bytes": len(raw),
    }


def redact_and_size_extra_safe(
    extra: Mapping[str, Any] | None,
    *,
    allowlist: frozenset[str] | None = None,
    max_json_bytes: int = _MAX_EXTRA_JSON_BYTES_DEFAULT,
) -> dict[str, Any]:
    """Same as ``redact_and_size_extra`` but never raises on bad types."""
    try:
        return redact_and_size_extra(extra, allowlist=allowlist, max_json_bytes=max_json_bytes)
    except Exception:
        return {"_redaction_error": True}
