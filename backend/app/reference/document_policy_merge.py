"""Reference R5 — platform document policy merge (pack + tenant overlay delta).

Resolved policy = deterministic merge(platform_pack, tenant_delta).
Tenant storage must be overlay/delta only — never a parallel policy fork.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Optional

from backend.app.document_types.registry import canonical_codes, normalize_input_doc_type
from backend.app.modules.documents.rules_engine import compute_candidate_checklist
from backend.app.reference.country_registry import country_registry_alpha2_set

_SPECS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "specs" / "platform"
PLATFORM_PACK_PATH = _SPECS_ROOT / "document-policy-platform-pack-v1.json"

_FORBIDDEN_FORK_KEYS = frozenset({"required", "optional", "requiredTypes", "optionalTypes"})
_ALLOWED_DELTA_ROOT_KEYS = frozenset({"candidate", "vacancy", "validity"})
_ALLOWED_CANDIDATE_DELTA_KEYS = frozenset({"overrides"})
_ALLOWED_VACANCY_DELTA_KEYS = frozenset({"additions"})


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Policy JSON must be an object: {path}")
    return payload


@lru_cache(maxsize=1)
def load_platform_pack_payload() -> dict[str, Any]:
    return _load_json(PLATFORM_PACK_PATH)


@lru_cache(maxsize=1)
def platform_ruleset_base() -> dict[str, Any]:
    payload = load_platform_pack_payload()
    ruleset = payload.get("ruleset")
    if not isinstance(ruleset, dict):
        raise ValueError("Platform pack must contain ruleset object")
    return copy.deepcopy(ruleset)


@lru_cache(maxsize=1)
def oswiadczenie_eligible_alpha2_lower() -> frozenset[str]:
    payload = load_platform_pack_payload()
    raw = payload.get("country_sets", {}).get("oswiadczenie_eligible_alpha2") or []
    registry = {code.lower() for code in country_registry_alpha2_set()}
    out = {str(code).strip().lower() for code in raw if str(code).strip()}
    unknown = sorted(out - registry)
    if unknown:
        raise ValueError(f"oswiadczenie_eligible_alpha2 codes not in Country Registry: {unknown}")
    return frozenset(out)


@lru_cache(maxsize=1)
def eu_member_alpha2_lower() -> frozenset[str]:
    from backend.app.reference.country_registry import list_country_registry_entries

    return frozenset(
        entry.identity.alpha2.lower()
        for entry in list_country_registry_entries()
        if entry.classifications.eu_member
    )


def _norm_doc_type(value: Any) -> str:
    return normalize_input_doc_type(str(value or ""))


def _normalize_type_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        code = _norm_doc_type(raw)
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def _normalize_ruleset_doc_types(ruleset: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(ruleset)
    candidate = out.setdefault("candidate", {})
    defaults = candidate.setdefault("defaults", {})
    defaults["requiredTypes"] = _normalize_type_list(defaults.get("requiredTypes"))
    defaults["optionalTypes"] = _normalize_type_list(defaults.get("optionalTypes"))

    normalized_overrides: list[dict[str, Any]] = []
    for rule in candidate.get("overrides") or []:
        if not isinstance(rule, dict):
            continue
        normalized_overrides.append(
            {
                **rule,
                "require": _normalize_type_list(rule.get("require")),
                "remove": _normalize_type_list(rule.get("remove")),
            }
        )
    candidate["overrides"] = normalized_overrides

    vacancy = out.setdefault("vacancy", {})
    normalized_additions: list[dict[str, Any]] = []
    for rule in vacancy.get("additions") or []:
        if not isinstance(rule, dict):
            continue
        normalized_additions.append({**rule, "require": _normalize_type_list(rule.get("require"))})
    vacancy["additions"] = normalized_additions

    validity = out.get("validity") or {}
    if isinstance(validity, dict):
        normalized_validity: dict[str, Any] = {}
        for key, value in validity.items():
            normalized_validity[_norm_doc_type(key)] = value
        out["validity"] = normalized_validity
    return out


def validate_tenant_overlay_delta(tenant_delta: Optional[Mapping[str, Any]]) -> None:
    """Reject tenant policy forks — only overlay deltas are allowed."""
    if not tenant_delta:
        return
    if not isinstance(tenant_delta, Mapping):
        raise ValueError("tenant_delta must be a mapping")

    for key in tenant_delta.keys():
        if key in _FORBIDDEN_FORK_KEYS:
            raise ValueError(f"tenant policy fork forbidden at root key: {key}")
        if key not in _ALLOWED_DELTA_ROOT_KEYS:
            raise ValueError(f"tenant_delta root key not allowed: {key}")

    candidate = tenant_delta.get("candidate")
    if candidate is not None:
        if not isinstance(candidate, Mapping):
            raise ValueError("tenant_delta.candidate must be a mapping")
        if "defaults" in candidate:
            raise ValueError("tenant_delta.candidate.defaults forbidden — platform pack owns defaults")
        for key in candidate.keys():
            if key not in _ALLOWED_CANDIDATE_DELTA_KEYS:
                raise ValueError(f"tenant_delta.candidate key not allowed: {key}")

    vacancy = tenant_delta.get("vacancy")
    if vacancy is not None:
        if not isinstance(vacancy, Mapping):
            raise ValueError("tenant_delta.vacancy must be a mapping")
        for key in vacancy.keys():
            if key not in _ALLOWED_VACANCY_DELTA_KEYS:
                raise ValueError(f"tenant_delta.vacancy key not allowed: {key}")

    validity = tenant_delta.get("validity")
    if validity is not None and not isinstance(validity, Mapping):
        raise ValueError("tenant_delta.validity must be a mapping")


def merge_resolved_policy(tenant_delta: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Merge platform pack with tenant overlay delta into resolved ruleset."""
    validate_tenant_overlay_delta(tenant_delta)
    merged = _normalize_ruleset_doc_types(platform_ruleset_base())

    if not tenant_delta:
        return merged

    delta = dict(tenant_delta)
    candidate_delta = delta.get("candidate") or {}
    if candidate_delta.get("overrides"):
        merged.setdefault("candidate", {}).setdefault("overrides", [])
        merged["candidate"]["overrides"].extend(copy.deepcopy(candidate_delta["overrides"]))

    vacancy_delta = delta.get("vacancy") or {}
    if vacancy_delta.get("additions"):
        merged.setdefault("vacancy", {}).setdefault("additions", [])
        merged["vacancy"]["additions"].extend(copy.deepcopy(vacancy_delta["additions"]))

    validity_delta = delta.get("validity") or {}
    if validity_delta:
        merged.setdefault("validity", {})
        for key, value in validity_delta.items():
            merged["validity"][_norm_doc_type(key)] = copy.deepcopy(value)

    return _normalize_ruleset_doc_types(merged)


def collect_pack_document_codes() -> frozenset[str]:
    ruleset = platform_ruleset_base()
    codes: set[str] = set()
    defaults = ((ruleset.get("candidate") or {}).get("defaults") or {})
    codes.update(_normalize_type_list(defaults.get("requiredTypes")))
    codes.update(_normalize_type_list(defaults.get("optionalTypes")))
    for rule in (ruleset.get("candidate") or {}).get("overrides") or []:
        codes.update(_normalize_type_list(rule.get("require")))
        codes.update(_normalize_type_list(rule.get("remove")))
    for rule in (ruleset.get("vacancy") or {}).get("additions") or []:
        codes.update(_normalize_type_list(rule.get("require")))
    codes.update(_norm_doc_type(key) for key in (ruleset.get("validity") or {}).keys())
    return frozenset(code for code in codes if code)


def candidate_requires_document(ctx: Mapping[str, Any], doc_type: str, *, tenant_delta: Optional[Mapping[str, Any]] = None) -> bool:
    """Q5 helper — is doc_type required for ctx under resolved policy?"""
    resolved = merge_resolved_policy(tenant_delta)
    checklist = compute_candidate_checklist(dict(ctx), resolved)
    target = _norm_doc_type(doc_type)
    required = {_norm_doc_type(code) for code in checklist.get("requiredTypes") or []}
    return target in required


__all__ = [
    "PLATFORM_PACK_PATH",
    "candidate_requires_document",
    "collect_pack_document_codes",
    "eu_member_alpha2_lower",
    "load_platform_pack_payload",
    "merge_resolved_policy",
    "oswiadczenie_eligible_alpha2_lower",
    "platform_ruleset_base",
    "validate_tenant_overlay_delta",
]
