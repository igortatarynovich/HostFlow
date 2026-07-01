"""Platform requirement catalog loader (bridge: slot_code → requirement_code per ADR-016)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_DATA_PATH = Path(__file__).resolve().parent / "data" / "requirement_slots.v1.json"

_EU_CITIZENSHIP = frozenset(
    {
        "at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie",
        "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se", "ch", "no", "is", "li",
    }
)


class RequirementSlotRegistryError(ValueError):
    pass


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def citizenship_group(citizenship: Optional[str]) -> str:
    cc = _norm(citizenship)
    if cc in _EU_CITIZENSHIP:
        return "eu"
    if cc:
        return "non_eu"
    return "unknown"


@lru_cache(maxsize=1)
def load_slot_registry() -> dict[str, Any]:
    if not _DATA_PATH.is_file():
        raise RequirementSlotRegistryError(f"Slot registry missing: {_DATA_PATH}")
    with _DATA_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RequirementSlotRegistryError("Slot registry root must be an object")
    slots = payload.get("slots")
    if not isinstance(slots, list):
        raise RequirementSlotRegistryError("Slot registry must contain slots[]")
    by_code: dict[str, dict[str, Any]] = {}
    for row in slots:
        if not isinstance(row, dict):
            raise RequirementSlotRegistryError("Each slot must be an object")
        code = _norm(row.get("requirement_code") or row.get("slot_code"))
        if not code:
            raise RequirementSlotRegistryError("Slot missing slot_code or requirement_code")
        if code in by_code:
            raise RequirementSlotRegistryError(f"Duplicate slot_code: {code}")
        alts = row.get("satisfaction_alternatives")
        if not isinstance(alts, list) or not alts:
            raise RequirementSlotRegistryError(f"Slot {code} must have satisfaction_alternatives[]")
        for alt in alts:
            if not isinstance(alt, dict):
                raise RequirementSlotRegistryError(f"Slot {code}: invalid alternative")
            any_of = alt.get("any_of") or []
            all_of = alt.get("all_of") or []
            if bool(any_of) == bool(all_of):
                raise RequirementSlotRegistryError(
                    f"Slot {code} alternative must have exactly one of any_of or all_of"
                )
        by_code[code] = row
    return {"version": payload.get("version"), "slots": slots, "by_code": by_code}


def get_slot_definition(slot_code: str) -> Optional[dict[str, Any]]:
    code = _norm(slot_code)
    if not code:
        return None
    registry = load_slot_registry()
    row = (registry.get("by_code") or {}).get(code)
    return dict(row) if isinstance(row, dict) else None


def get_requirement_definition(requirement_code: str) -> Optional[dict[str, Any]]:
    """Alias for catalog lookup (requirement_code == slot_code in bridge catalog)."""
    return get_slot_definition(requirement_code)


def list_slot_definitions() -> list[dict[str, Any]]:
    registry = load_slot_registry()
    return [dict(row) for row in registry.get("slots") or [] if isinstance(row, dict)]


def slot_applies(
    slot: dict[str, Any],
    *,
    citizenship: Optional[str] = None,
    position_category: Optional[str] = None,
) -> bool:
    """Return False when slot is not applicable (treated as not_applicable / N/A)."""
    skip = slot.get("not_applicable_when")
    if not isinstance(skip, dict):
        return True
    group = skip.get("citizenship_group")
    if group is not None and _norm(group):
        if citizenship_group(citizenship) == _norm(group):
            return False
    required_positions = skip.get("position_category_in")
    if isinstance(required_positions, list) and required_positions:
        actual = _norm(position_category)
        allowed = {_norm(x) for x in required_positions}
        if actual not in allowed:
            return False
    return True


__all__ = [
    "RequirementSlotRegistryError",
    "citizenship_group",
    "get_requirement_definition",
    "get_slot_definition",
    "list_slot_definitions",
    "load_slot_registry",
    "slot_applies",
]
