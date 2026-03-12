"""Data normalization: transliteration and latin display helpers."""

from __future__ import annotations

from typing import Optional

from backend.app.services.transliterate import has_cyrillic, transliterate


def _as_str(val: Optional[str | dict]) -> Optional[str]:
    """Convert value to string; if dict, join values with space."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        parts = [str(v) for v in val.values() if v]
        return " ".join(parts) if parts else None
    return str(val)


def ensure_latin_fields(
    *,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    city: Optional[str] = None,
    address: Optional[str | dict] = None,
) -> dict[str, Optional[str]]:
    """
    Compute _latin values for fields that contain Cyrillic.
    Returns dict with first_name_latin, last_name_latin, city_latin, address_latin.
    Address can be string or dict (structured address); dict is normalized to string.
    """
    result: dict[str, Optional[str]] = {}
    if first_name and isinstance(first_name, str) and has_cyrillic(first_name):
        result["first_name_latin"] = transliterate(first_name)
    else:
        result["first_name_latin"] = None
    if last_name and isinstance(last_name, str) and has_cyrillic(last_name):
        result["last_name_latin"] = transliterate(last_name)
    else:
        result["last_name_latin"] = None
    city_str = _as_str(city) if city is not None else None
    if city_str and has_cyrillic(city_str):
        result["city_latin"] = transliterate(city_str)
    else:
        result["city_latin"] = None
    addr_str = _as_str(address) if address is not None else None
    if addr_str and has_cyrillic(addr_str):
        result["address_latin"] = transliterate(addr_str)
    else:
        result["address_latin"] = None
    return result


def display_for_client(
    original: Optional[str],
    latin: Optional[str],
) -> str:
    """
    Return value to show to client: latin if present and original has Cyrillic, else original.
    """
    if not original:
        return ""
    if latin:
        return latin
    return original
