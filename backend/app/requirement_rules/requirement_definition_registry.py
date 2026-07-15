"""Canonical RequirementDefinition registry loader (ADR-018)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_DATA_PATH = Path(__file__).resolve().parent / "data" / "requirement_definitions.v1.json"


class RequirementDefinitionRegistryError(ValueError):
    pass


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


@lru_cache(maxsize=1)
def load_requirement_definitions_payload() -> dict[str, Any]:
    if not _DATA_PATH.is_file():
        raise RequirementDefinitionRegistryError(f"Requirement definitions missing: {_DATA_PATH}")
    with _DATA_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RequirementDefinitionRegistryError("Requirement definitions root must be an object")
    return payload


@lru_cache(maxsize=1)
def requirement_definitions_by_code() -> dict[str, dict[str, Any]]:
    payload = load_requirement_definitions_payload()
    rows = payload.get("requirements")
    if not isinstance(rows, list):
        raise RequirementDefinitionRegistryError("requirements[] required")

    by_code: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RequirementDefinitionRegistryError("Each requirement must be an object")
        code = _norm(row.get("requirement_code"))
        if not code:
            raise RequirementDefinitionRegistryError("requirement_code required")
        if code in by_code:
            raise RequirementDefinitionRegistryError(f"Duplicate requirement_code: {code}")
        alts = row.get("alternatives")
        if not isinstance(alts, list) or not alts:
            raise RequirementDefinitionRegistryError(f"{code}: alternatives[] required")
        for alt in alts:
            if not isinstance(alt, dict):
                raise RequirementDefinitionRegistryError(f"{code}: invalid alternative")
            if not alt.get("alternative_code"):
                raise RequirementDefinitionRegistryError(f"{code}: alternative_code required")
            conditions = alt.get("conditions")
            if not isinstance(conditions, list) or not conditions:
                raise RequirementDefinitionRegistryError(
                    f"{code}/{alt.get('alternative_code')}: conditions[] required"
                )
        by_code[code] = row
    return by_code


def get_requirement_definition_v1(requirement_code: str) -> Optional[dict[str, Any]]:
    code = _norm(requirement_code)
    row = requirement_definitions_by_code().get(code)
    return dict(row) if isinstance(row, dict) else None


def list_requirement_definitions_v1() -> list[dict[str, Any]]:
    return [dict(row) for row in requirement_definitions_by_code().values()]


def requirement_definitions_version() -> str:
    return str(load_requirement_definitions_payload().get("registry_version") or "unknown")


__all__ = [
    "RequirementDefinitionRegistryError",
    "get_requirement_definition_v1",
    "list_requirement_definitions_v1",
    "load_requirement_definitions_payload",
    "requirement_definitions_by_code",
    "requirement_definitions_version",
]
