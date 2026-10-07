"""Requirement Policy Operator (RPM-2) — Documents-first compiler + view.

Contract id: ``requirement_policy_operator.v1``.

Public write is require/remove/reason/expected_revision — not arbitrary
tenant_delta. Compiler emits R5 overlay shape, then validate_tenant_overlay_delta.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

from backend.app.document_types.registry import is_canonical_code
from backend.app.reference.document_policy_merge import (
    platform_ruleset_base,
    validate_tenant_overlay_delta,
)
from backend.app.reference.requirement_policy_authority import WRITE_AUTHORITY
from backend.app.services.document_hub_delivery_contract import (
    evaluate_required_doc_applicability_via_contract,
)

CONTRACT_ID: Final[str] = "requirement_policy_operator.v1"
AUDIT_ACTION: Final[str] = "requirement_policy.overlay.updated"
EMPTY_REVISION: Final[int] = 0


class OperatorOverlayError(ValueError):
    """Operator input rejected before persistence."""


def _norm_code_list(values: Any, *, field: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise OperatorOverlayError(f"{field} must be a list of document type codes")
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        code = str(raw or "").strip().lower().replace("-", "_")
        if not code:
            raise OperatorOverlayError(f"{field} contains an empty code")
        if not is_canonical_code(code):
            raise OperatorOverlayError(
                f"{field} contains noncanonical document code: {code}"
            )
        if code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def compile_operator_overlay_delta(
    *,
    require: Any = None,
    remove: Any = None,
) -> dict[str, Any]:
    """Compile Documents-first require/remove into R5 tenant_delta.

    Empty require and remove → ``{}`` (reset to platform base).
    Otherwise one unconditional candidate override rule.
    """
    require_codes = _norm_code_list(require, field="require")
    remove_codes = _norm_code_list(remove, field="remove")
    overlap = sorted(set(require_codes) & set(remove_codes))
    if overlap:
        raise OperatorOverlayError(
            "require and remove must not share codes: " + ", ".join(overlap)
        )
    if not require_codes and not remove_codes:
        delta: dict[str, Any] = {}
    else:
        rule: dict[str, Any] = {"when": {}}
        if require_codes:
            rule["require"] = require_codes
        if remove_codes:
            rule["remove"] = remove_codes
        delta = {"candidate": {"overrides": [rule]}}
    validate_tenant_overlay_delta(delta)
    return delta


def project_operator_override(delta: Mapping[str, Any] | None) -> dict[str, list[str]]:
    """Project stored R5 delta back to Documents-first require/remove."""
    require: list[str] = []
    remove: list[str] = []
    if not delta:
        return {"require": require, "remove": remove}
    candidate = delta.get("candidate") if isinstance(delta, Mapping) else None
    overrides = (candidate or {}).get("overrides") if isinstance(candidate, Mapping) else None
    if not isinstance(overrides, list):
        return {"require": require, "remove": remove}
    for rule in overrides:
        if not isinstance(rule, Mapping):
            continue
        when = rule.get("when")
        if when not in (None, {}, []):
            # RPM-2 Documents-first surface only projects unconditional rules.
            continue
        for code in rule.get("require") or []:
            c = str(code or "").strip()
            if c and c not in require:
                require.append(c)
        for code in rule.get("remove") or []:
            c = str(code or "").strip()
            if c and c not in remove:
                remove.append(c)
    return {"require": require, "remove": remove}


def pack_defaults_metadata() -> dict[str, list[str]]:
    ruleset = platform_ruleset_base()
    defaults = ((ruleset.get("candidate") or {}).get("defaults") or {})
    return {
        "requiredTypes": list(defaults.get("requiredTypes") or []),
        "optionalTypes": list(defaults.get("optionalTypes") or []),
    }


def build_operator_view(
    *,
    delta: Mapping[str, Any] | None,
    reason: str,
    revision: int,
    preview_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """base = evaluate without delta; result = evaluate with stored delta."""
    ctx = dict(preview_context or {})
    stored = dict(delta or {})
    base = evaluate_required_doc_applicability_via_contract(ctx, tenant_delta=None)
    result = evaluate_required_doc_applicability_via_contract(
        ctx, tenant_delta=stored if stored else None
    )
    projection = project_operator_override(stored)
    return {
        "contract_id": CONTRACT_ID,
        "write_authority": WRITE_AUTHORITY,
        "base": base,
        "override": {
            "require": projection["require"],
            "remove": projection["remove"],
            "revision": revision,
            "reason": reason,
        },
        "reason": reason,
        "revision": revision,
        "result": result,
        "preview_context": ctx,
        "pack_defaults": pack_defaults_metadata(),
    }


def validate_reason(reason: Any) -> str:
    text = str(reason or "").strip()
    if len(text) < 3:
        raise OperatorOverlayError("reason must be at least 3 characters")
    if len(text) > 2000:
        raise OperatorOverlayError("reason must be at most 2000 characters")
    return text
