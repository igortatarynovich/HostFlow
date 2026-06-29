"""Flatten recruitment / handoff address objects for HR verification profile context."""

from __future__ import annotations

from typing import Any, Optional

_ADDRESS_PART_KEYS = ("country", "city", "street", "house", "apt", "zip", "postal_code", "line1", "address")


def coerce_address_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key in _ADDRESS_PART_KEYS:
        raw = value.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            out[key] = text
    if out.get("postal_code") and not out.get("zip"):
        out["zip"] = out["postal_code"]
    return out


def format_address_line(addr: dict[str, str]) -> Optional[str]:
    if not addr:
        return None
    parts: list[str] = []
    street_line = " ".join(p for p in (addr.get("street"), addr.get("house")) if p).strip()
    if street_line:
        parts.append(street_line)
    if addr.get("apt"):
        parts.append(addr["apt"])
    locality = " ".join(p for p in (addr.get("zip"), addr.get("city")) if p).strip()
    if locality:
        parts.append(locality)
    if addr.get("country"):
        parts.append(addr["country"])
    line = ", ".join(parts)
    return line or None


def _assign_if_empty(target: dict[str, Any], key: str, value: Optional[str]) -> None:
    if not value or not str(value).strip():
        return
    current = target.get(key)
    if current is None or (isinstance(current, str) and not current.strip()):
        target[key] = str(value).strip()


def promote_address_fields(target: dict[str, Any], *sources: Any) -> None:
    """Write flattened address_* keys into a snapshot-like dict."""
    merged: dict[str, str] = {}
    for src in sources:
        chunk = coerce_address_dict(src)
        for key, value in chunk.items():
            merged.setdefault(key, value)
    if not merged:
        return
    _assign_if_empty(target, "address_country", merged.get("country"))
    _assign_if_empty(target, "city", merged.get("city"))
    zip_value = merged.get("zip") or merged.get("postal_code")
    _assign_if_empty(target, "postal_code", zip_value)
    _assign_if_empty(target, "address_street", merged.get("street"))
    _assign_if_empty(target, "address_house", merged.get("house"))
    _assign_if_empty(target, "address_apt", merged.get("apt"))
    line = format_address_line(merged)
    _assign_if_empty(target, "address_line", line)


def address_dict_complete(addr: Any) -> bool:
    parsed = coerce_address_dict(addr)
    if not parsed:
        return False
    return bool(
        (parsed.get("country") and parsed.get("city") and parsed.get("street"))
        or format_address_line(parsed)
    )
