"""RPM-3B consumer parity — policy-answer helper over existing R5 merge.

Same pack + same tenant_delta → same required-set membership as
``evaluate_required_doc_applicability_via_contract``. Not a second merge,
evaluator, overlay store, or write of the operator question.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

CONTRACT_ID: Final[str] = "requirement_policy_consumer_parity.v1"

PROOF_X_REQUIRE: Final[str] = "adr_certificate"
PROOF_X_REMOVE: Final[str] = "passport"


def preview_context() -> dict[str, Any]:
    """Shared empty owner context for the three consume-parity scenarios."""
    return {}


def require_overlay_delta(code: str = PROOF_X_REQUIRE) -> dict[str, Any]:
    return {"vacancy": {"additions": [{"when": {}, "require": [str(code)]}]}}


def remove_overlay_delta(code: str = PROOF_X_REMOVE) -> dict[str, Any]:
    return {"candidate": {"overrides": [{"when": {}, "remove": [str(code)]}]}}


def r5_required_set(
    owner_context: Mapping[str, Any] | None = None,
    tenant_delta: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """Canonical required-set membership for the operator question."""
    from backend.app.services.document_hub_delivery_contract import (
        APPLICABILITY_REQUIRED,
        evaluate_required_doc_applicability_via_contract,
    )

    result = evaluate_required_doc_applicability_via_contract(
        owner_context,
        tenant_delta=tenant_delta,
    )
    out: set[str] = set()
    for row in result.get("applicability") or []:
        if not isinstance(row, Mapping):
            continue
        if row.get("applicability") != APPLICABILITY_REQUIRED:
            continue
        code = str(row.get("doc_type") or "").strip().lower()
        if code:
            out.add(code)
    return frozenset(out)


def engine_document_required_set(
    profile_view: Mapping[str, Any],
    *,
    context: str = "readiness",
    tenant_delta: Mapping[str, Any] | None = None,
    owner_context: Mapping[str, Any] | None = None,
    stage_code: str | None = None,
) -> frozenset[str]:
    """Policy answer from Engine document_required *input* (before slot orchestration)."""
    del profile_view, stage_code
    from backend.app.requirement_rules.registry import build_document_required_rules

    rules = build_document_required_rules(
        pack_code="",
        entity_profile_code="",
        context=context,
        tenant_delta=dict(tenant_delta) if tenant_delta is not None else None,
        owner_context=dict(owner_context) if owner_context is not None else None,
    )
    out: set[str] = set()
    for row in rules:
        if not isinstance(row, Mapping):
            continue
        code = str(row.get("document_type_code") or row.get("target") or "").strip().lower()
        if code:
            out.add(code)
    return frozenset(out)


def leftover_ruleset_payload() -> dict[str, Any]:
    """Leftover ruleset JSON that disagrees with R5 — must not win as required-set SoT."""
    return {
        "candidate": {
            "defaults": {
                "requiredTypes": ["code95", "national_id"],
                "optionalTypes": ["passport", "adr_certificate"],
            }
        }
    }


def overlay_r5_required_on_expected_rows(
    rows: list[Mapping[str, Any]] | None,
    owner_context: Mapping[str, Any] | None = None,
    tenant_delta: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Stamp ``required`` from R5 onto expected-document rows; inject missing R5 codes."""
    r5 = r5_required_set(owner_context, tenant_delta)
    out_by_code: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        code = str(row.get("document_code") or "").strip().lower()
        if not code:
            continue
        updated = dict(row)
        in_r5 = code in r5
        updated["required"] = in_r5
        updated["candidate_policy_required"] = in_r5
        out_by_code[code] = updated
    for code in r5:
        if code in out_by_code:
            continue
        out_by_code[code] = {
            "document_code": code,
            "label": code,
            "group": "other",
            "required": True,
            "candidate_policy_required": True,
            "source_pack": "r5_merge",
            "reason": "required by R5 merge(pack, tenant_delta)",
        }
    return list(out_by_code.values())


def seal_checklist_required_types(
    checklist: Mapping[str, Any] | None,
    owner_context: Mapping[str, Any] | None = None,
    tenant_delta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    out = dict(checklist or {})
    out["requiredTypes"] = sorted(r5_required_set(owner_context, tenant_delta))
    return out


def expected_rows_required_set(rows: list[Mapping[str, Any]] | None) -> frozenset[str]:
    return frozenset(
        str(row.get("document_code") or "").strip().lower()
        for row in (rows or [])
        if isinstance(row, Mapping)
        and bool(row.get("required") or row.get("candidate_policy_required"))
        and str(row.get("document_code") or "").strip()
    )


def pack_grouping_required_set(
    owner_context: Mapping[str, Any] | None = None,
    tenant_delta: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """Union of Hub pack `required` lists — must be ⊆ R5, never invent X."""
    from backend.app.modules.documents.pack_definitions import (
        DOCUMENT_PACK_DEFINITIONS,
        required_codes_for_pack,
    )

    ctx = dict(owner_context or {})
    if tenant_delta is not None:
        ctx["tenant_delta"] = tenant_delta
    out: set[str] = set()
    for pack in DOCUMENT_PACK_DEFINITIONS:
        out.update(required_codes_for_pack(pack, ctx))
    return frozenset(out)


def owner_summary_required_set(
    owner_context: Mapping[str, Any] | None = None,
    tenant_delta: Mapping[str, Any] | None = None,
    *,
    leftover_ruleset: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """Policy answer from owner_summary even if a leftover ruleset payload is passed."""
    from backend.app.modules.documents.owner_summary import compute_owner_summary

    ctx = dict(owner_context or {})
    if tenant_delta is not None:
        ctx["tenant_delta"] = tenant_delta
    summary = compute_owner_summary(ctx, dict(leftover_ruleset or {}), [])
    checklist = summary.get("checklist") if isinstance(summary, dict) else None
    required = []
    if isinstance(checklist, Mapping):
        required = list(checklist.get("requiredTypes") or [])
    return frozenset(str(code).strip().lower() for code in required if str(code).strip())


def transfer_candidate_required_set(
    owner_context: Mapping[str, Any] | None = None,
    tenant_delta: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """Candidate-required subset for transfer — R5, not transfer-operation extras."""
    return r5_required_set(owner_context, tenant_delta)


def hiring_policy_required_set(
    owner_context: Mapping[str, Any] | None = None,
    tenant_delta: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """Hiring pipeline required-set via owner_summary (stage gates stay derivative)."""
    return owner_summary_required_set(
        owner_context,
        tenant_delta,
        leftover_ruleset=leftover_ruleset_payload(),
    )


CONSUMER_CLASSIFICATION: Final[dict[str, str]] = {
    "A": "consume",
    "B": "consume",
    "C": "consume",
    "D": "leftover-out-of-scope",
    "E": "consume",
    "F": "consume",
    "G": "consume",
    "H": "already-parity",
    "I": "already-parity",
    "requirement_checker_gates": "leftover-out-of-scope",
    "documents_eta_legacy_codes": "leftover-out-of-scope",
}


__all__ = [
    "CONSUMER_CLASSIFICATION",
    "CONTRACT_ID",
    "PROOF_X_REMOVE",
    "PROOF_X_REQUIRE",
    "engine_document_required_set",
    "expected_rows_required_set",
    "hiring_policy_required_set",
    "leftover_ruleset_payload",
    "overlay_r5_required_on_expected_rows",
    "owner_summary_required_set",
    "pack_grouping_required_set",
    "preview_context",
    "r5_required_set",
    "remove_overlay_delta",
    "require_overlay_delta",
    "seal_checklist_required_types",
    "transfer_candidate_required_set",
]
