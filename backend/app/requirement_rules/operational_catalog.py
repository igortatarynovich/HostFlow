"""A3-B4 — Operational requirements catalog loader."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent / "data" / "operational_requirements.v1.json"


class OperationalRequirementsCatalogError(ValueError):
    pass


def _norm(value: Any) -> str:
    return str(value or "").strip()


@lru_cache(maxsize=1)
def load_operational_requirements_catalog() -> dict[str, Any]:
    if not _DATA_PATH.is_file():
        raise OperationalRequirementsCatalogError(f"Operational catalog missing: {_DATA_PATH}")
    with _DATA_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise OperationalRequirementsCatalogError("Operational catalog root must be an object")
    rows = payload.get("requirements")
    if not isinstance(rows, list):
        raise OperationalRequirementsCatalogError("Operational catalog must contain requirements[]")
    by_code: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise OperationalRequirementsCatalogError("Each requirement must be an object")
        code = _norm(row.get("requirement_code"))
        if not code:
            raise OperationalRequirementsCatalogError("Requirement missing requirement_code")
        if code in by_code:
            raise OperationalRequirementsCatalogError(f"Duplicate requirement_code: {code}")
        by_code[code] = row
    return {"version": payload.get("version"), "requirements": rows, "by_code": by_code}


def get_operational_requirement_definition(requirement_code: str) -> dict[str, Any] | None:
    catalog = load_operational_requirements_catalog()
    by_code = catalog.get("by_code") or {}
    if not isinstance(by_code, dict):
        return None
    row = by_code.get(_norm(requirement_code))
    return row if isinstance(row, dict) else None


def operational_requirements_for_profile(entity_profile_code: str | None) -> list[dict[str, Any]]:
    catalog = load_operational_requirements_catalog()
    profile = _norm(entity_profile_code)
    rows: list[dict[str, Any]] = []
    for row in catalog.get("requirements") or []:
        if not isinstance(row, dict):
            continue
        allowed = row.get("entity_profile_codes") or []
        if isinstance(allowed, list) and allowed:
            codes = {_norm(item) for item in allowed if _norm(item)}
            if profile and profile not in codes:
                continue
        rows.append(row)
    return rows


__all__ = [
    "OperationalRequirementsCatalogError",
    "get_operational_requirement_definition",
    "load_operational_requirements_catalog",
    "operational_requirements_for_profile",
]
