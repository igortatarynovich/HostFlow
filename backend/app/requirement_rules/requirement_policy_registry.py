"""Versioned RequirementPolicy registry loader (ADR-018)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

_POLICY_DIR = Path(__file__).resolve().parent / "data"
_DRIVER_CE_POLICY_PATH = _POLICY_DIR / "requirement_policy.recruitment.driver_ce.pl.v1.json"

ENTITY_PROFILE_TO_DEFAULT_POLICY: dict[str, str] = {
    "recruitment.candidate.driver_ce": "recruitment.driver_ce.pl/v1",
    "recruitment.candidate.driver_ce_ua": "recruitment.driver_ce.pl/v1",
}


class RequirementPolicyRegistryError(ValueError):
    pass


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _load_policy_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RequirementPolicyRegistryError(f"Policy file missing: {path}")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RequirementPolicyRegistryError(f"Policy root must be object: {path.name}")
    return payload


def _validate_policy(payload: dict[str, Any], *, path: Path) -> None:
    policy_ref = str(payload.get("policy_ref") or "").strip()
    if not policy_ref:
        raise RequirementPolicyRegistryError(f"{path.name}: policy_ref required")
    expected_ref = f"{payload.get('policy_code')}/{payload.get('policy_version')}"
    if policy_ref != expected_ref:
        raise RequirementPolicyRegistryError(
            f"{path.name}: policy_ref '{policy_ref}' != '{expected_ref}'"
        )
    bindings = payload.get("requirement_bindings") or payload.get("requirements")
    if not isinstance(bindings, list) or not bindings:
        raise RequirementPolicyRegistryError(f"{path.name}: requirement_bindings[] required")
    seen: set[str] = set()
    for row in bindings:
        if not isinstance(row, dict):
            raise RequirementPolicyRegistryError(f"{path.name}: invalid requirement binding")
        code = _norm(row.get("requirement_code"))
        if not code or code in seen:
            raise RequirementPolicyRegistryError(f"{path.name}: duplicate/empty requirement_code")
        seen.add(code)
        ownership = row.get("stage_ownership") if isinstance(row.get("stage_ownership"), dict) else row
        if not ownership.get("blocks_stage") or not ownership.get("required_by_stage"):
            raise RequirementPolicyRegistryError(f"{path.name}/{code}: stage ownership fields required")
    deps = payload.get("dependency_rules")
    if not isinstance(deps, list):
        raise RequirementPolicyRegistryError(f"{path.name}: dependency_rules[] required")
    apps = payload.get("applicability_rules")
    if not isinstance(apps, list):
        raise RequirementPolicyRegistryError(f"{path.name}: applicability_rules[] required")


@lru_cache(maxsize=1)
def load_registered_policies() -> dict[str, dict[str, Any]]:
    policies: dict[str, dict[str, Any]] = {}
    for path in sorted(_POLICY_DIR.glob("requirement_policy.*.json")):
        payload = _load_policy_file(path)
        _validate_policy(payload, path=path)
        ref = str(payload["policy_ref"])
        if ref in policies:
            raise RequirementPolicyRegistryError(f"Duplicate policy_ref: {ref}")
        policies[ref] = payload
    return policies


def get_requirement_policy(policy_ref: str) -> Optional[dict[str, Any]]:
    ref = str(policy_ref or "").strip()
    if not ref:
        return None
    row = load_registered_policies().get(ref)
    return dict(row) if isinstance(row, dict) else None


def get_policy_requirement(policy_ref: str, requirement_code: str) -> Optional[dict[str, Any]]:
    policy = get_requirement_policy(policy_ref)
    if not policy:
        return None
    target = _norm(requirement_code)
    bindings = policy.get("requirement_bindings") or policy.get("requirements") or []
    for row in bindings:
        if isinstance(row, dict) and _norm(row.get("requirement_code")) == target:
            return dict(row)
    return None


def policy_blocks_stage(policy_ref: str, requirement_code: str) -> Optional[str]:
    row = get_policy_requirement(policy_ref, requirement_code)
    if not row:
        return None
    ownership = row.get("stage_ownership") if isinstance(row.get("stage_ownership"), dict) else row
    return str(ownership.get("blocks_stage") or "") or None


def default_policy_ref_for_entity_profile(entity_profile_code: str) -> Optional[str]:
    return ENTITY_PROFILE_TO_DEFAULT_POLICY.get(str(entity_profile_code or "").strip())


__all__ = [
    "ENTITY_PROFILE_TO_DEFAULT_POLICY",
    "RequirementPolicyRegistryError",
    "default_policy_ref_for_entity_profile",
    "get_policy_requirement",
    "get_requirement_policy",
    "load_registered_policies",
    "policy_blocks_stage",
]
