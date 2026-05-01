from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (dict, list)):
        return ""
    return str(value)


def _binding_value(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, Mapping):
        inner = raw.get("value")
        fmt = str(raw.get("format") or "").strip().lower()
        if fmt == "date" and inner:
            try:
                if isinstance(inner, str):
                    return inner[:10]
            except Exception:
                pass
        if inner is not None:
            return _stringify(inner)
    return _stringify(raw)


def resolve_path(ctx: Mapping[str, Any], dotted: str) -> Any:
    cur: Any = ctx
    for part in dotted.split("."):
        if not part:
            continue
        if isinstance(cur, Mapping):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
        if cur is None:
            return None
    return cur


def render_merge_text(
    body: str,
    *,
    context: Mapping[str, Any],
    variable_bindings: Mapping[str, Any] | None,
) -> str:
    bindings = dict(variable_bindings or {})

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key in bindings:
            return _binding_value(bindings[key])
        val = resolve_path(context, key)
        return _stringify(val)

    return _PLACEHOLDER_RE.sub(replace, body)
