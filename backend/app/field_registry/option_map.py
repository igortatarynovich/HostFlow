"""Option-map lookup shared by Mapping workspace, ingest, and conversion.

Graph answers often arrive snake_cased (`виза`, `более_2_лет`) while the
operator saved labels (`Виза`, `Более 2 лет`). Matching is case-insensitive
and treats `_` / `-` as spaces. Not a second mapping engine.
"""

from __future__ import annotations

from typing import Any, Mapping

OPTION_IGNORE_VALUE = "__ignore__"


def normalize_option_key(raw: Any) -> str:
    text = str(raw or "").strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def lookup_option_map(option_map: Mapping[str, Any] | None, value: Any) -> str | None:
    """Return mapped dest value, ``OPTION_IGNORE_VALUE``, or None if no decision."""
    if not option_map or value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in option_map:
        mapped = option_map[text]
    else:
        mapped = None
        want = normalize_option_key(text)
        if not want:
            return None
        for key, dest in option_map.items():
            if normalize_option_key(key) == want:
                mapped = dest
                break
        if mapped is None:
            return None
    out = str(mapped).strip()
    return out or None


def option_map_covers(option_map: Mapping[str, Any] | None, options: list[str] | tuple[str, ...]) -> bool:
    if not options:
        return True
    decided = {normalize_option_key(k) for k in (option_map or {}) if str(k).strip()}
    decided.discard("")
    return all(normalize_option_key(opt) in decided for opt in options)
