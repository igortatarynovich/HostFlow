from __future__ import annotations

from datetime import date
from typing import Any, Optional

from backend.app.services.document_catalog import get_doc_type_defaults, normalize_doc_type
from backend.app.services.document_expiry_engine import (
    ExpiryEvaluation,
    aggregate_document_expiry_states,
    evaluate_document_expiry,
    owner_expiry_aggregate_to_dict,
)

from .pack_definitions import DOCUMENT_PACK_DEFINITIONS, DocumentPackDefinition, required_codes_for_pack
from .rules_engine import expiring_threshold_for, expiry_required_for


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_type_code(value: Any) -> str:
    raw = _norm(value)
    if not raw:
        return ""
    compact = raw.replace("-", "_").replace(" ", "_")
    canonical = normalize_doc_type(compact)
    if canonical and canonical != "additional_document":
        return canonical
    return compact


def _alias_codes(code: str) -> set[str]:
    canonical = _normalize_type_code(code)
    aliases = {canonical}
    defaults = get_doc_type_defaults(canonical)
    for alias in defaults.aliases:
        aliases.add(_normalize_type_code(alias))
    legacy = {
        "code_95": {"code95", "qualification_code95"},
        "tachograph_card": {"tacho_card", "tachograph"},
        "id_card": {"national_id", "identity_document"},
        "psychotest": {"psychotest", "psych_tests", "psycho_test"},
    }
    aliases.update(legacy.get(canonical, set()))
    return {item for item in aliases if item}


def _docs_for_code(docs: list[dict[str, Any]], code: str) -> list[dict[str, Any]]:
    targets = _alias_codes(code)
    out: list[dict[str, Any]] = []
    for doc in docs:
        doc_type = _normalize_type_code(doc.get("type") or doc.get("doc_type"))
        if doc_type in targets:
            out.append(doc)
    return out


def _evaluate_doc(
    doc: dict[str, Any],
    *,
    ruleset: dict[str, Any],
    reference_date: date,
    fallback_code: str,
) -> ExpiryEvaluation:
    doc_type = _normalize_type_code(doc.get("type") or doc.get("doc_type")) or fallback_code
    expires_at = doc.get("expires_at") or doc.get("expire_date")
    return evaluate_document_expiry(
        expires_on=expires_at,
        expiry_required=expiry_required_for(doc_type, ruleset),
        reference_date=reference_date,
        expiring_soon_days=expiring_threshold_for(doc_type, ruleset),
    )


def _resolve_required_code_state(
    code: str,
    docs: list[dict[str, Any]],
    *,
    ruleset: dict[str, Any],
    reference_date: date,
) -> tuple[str, Optional[ExpiryEvaluation]]:
    matches = _docs_for_code(docs, code)
    if not matches:
        return "missing", None

    evaluations = [_evaluate_doc(doc, ruleset=ruleset, reference_date=reference_date, fallback_code=code) for doc in matches]
    states = [item.state for item in evaluations]
    if any(state == "valid" for state in states):
        picked = next(item for item in evaluations if item.state == "valid")
        return "present", picked
    if any(state == "expiring_soon" for state in states):
        picked = next(item for item in evaluations if item.state == "expiring_soon")
        return "expiring_soon", picked
    if any(state == "missing_expiry" for state in states):
        picked = next(item for item in evaluations if item.state == "missing_expiry")
        return "missing_expiry", picked
    picked = next(item for item in evaluations if item.state == "expired")
    return "expired", picked


def _pack_status(*, gaps: list[str], warnings: list[str], skeleton: bool) -> str:
    if skeleton:
        return "skeleton"
    if gaps:
        return "gaps"
    if warnings:
        return "warnings"
    return "valid"


def project_document_pack(
    pack: DocumentPackDefinition,
    *,
    ctx: dict[str, Any],
    ruleset: dict[str, Any],
    docs: list[dict[str, Any]],
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    today = reference_date or date.today()
    required_codes = list(required_codes_for_pack(pack, ctx))

    present: list[str] = []
    missing: list[str] = []
    expired: list[str] = []
    expiring_soon: list[dict[str, Any]] = []
    missing_expiry: list[str] = []
    gaps: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    evaluations: list[ExpiryEvaluation] = []

    for code in required_codes:
        state, evaluation = _resolve_required_code_state(code, docs, ruleset=ruleset, reference_date=today)
        if state == "missing":
            missing.append(code)
            gaps.append(code)
            blockers.append(code)
            continue

        present.append(code)
        if evaluation is not None:
            evaluations.append(evaluation)

        if state == "expired":
            expired.append(code)
            gaps.append(code)
            blockers.append(code)
        elif state == "missing_expiry":
            missing_expiry.append(code)
            gaps.append(code)
            blockers.append(code)
        elif state == "expiring_soon" and evaluation is not None:
            expiring_soon.append(
                {
                    "document_code": code,
                    "expires_on": str(evaluation.expires_on) if evaluation.expires_on else None,
                    "days_left": evaluation.days_left,
                }
            )
            warnings.append(code)

    expiry = owner_expiry_aggregate_to_dict(aggregate_document_expiry_states(evaluations))

    return {
        "code": pack.code,
        "label": pack.label,
        "status": _pack_status(gaps=gaps, warnings=warnings, skeleton=pack.skeleton),
        "skeleton": pack.skeleton,
        "applies": bool(pack.skeleton or required_codes),
        "ref_pack_codes": list(pack.ref_pack_codes),
        "required": required_codes,
        "present": present,
        "missing": missing,
        "expired": expired,
        "expiring_soon": expiring_soon,
        "missing_expiry": missing_expiry,
        "gaps": gaps,
        "blockers": blockers,
        "warnings": warnings,
        "expiry": expiry,
    }


def project_document_packs(
    ctx: dict[str, Any],
    ruleset: dict[str, Any],
    docs: list[dict[str, Any]],
    *,
    reference_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    return [
        project_document_pack(
            pack,
            ctx=ctx,
            ruleset=ruleset,
            docs=docs,
            reference_date=reference_date,
        )
        for pack in DOCUMENT_PACK_DEFINITIONS
        if pack.skeleton or pack.applies(ctx)
    ]


def project_document_packs_from_expected(
    *,
    ctx: dict[str, Any],
    ruleset: dict[str, Any],
    docs: list[dict[str, Any]],
    expected_documents: list[dict[str, Any]],
    reference_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    """
    Pack projection grouped by applicability resolver rows.

    Preserves module-owned policy by using expected document requirements from
    applicability output, then applying expiry engine on present documents.
    """
    today = reference_date or date.today()
    expected_by_code = {_norm(row.get("document_code")): row for row in expected_documents if row.get("document_code")}

    packs: list[dict[str, Any]] = []
    for pack in DOCUMENT_PACK_DEFINITIONS:
        if pack.skeleton:
            packs.append(
                project_document_pack(pack, ctx=ctx, ruleset=ruleset, docs=docs, reference_date=today)
            )
            continue
        if not pack.applies(ctx):
            continue

        pack_code_set = {_norm(code) for code in required_codes_for_pack(pack, ctx)}
        required_codes = [
            str(row["document_code"])
            for row in expected_documents
            if _norm(row.get("document_code")) in pack_code_set and bool(row.get("required"))
        ]

        present: list[str] = []
        missing: list[str] = []
        expired: list[str] = []
        expiring_soon: list[dict[str, Any]] = []
        missing_expiry: list[str] = []
        gaps: list[str] = []
        blockers: list[str] = []
        warnings: list[str] = []
        evaluations: list[ExpiryEvaluation] = []

        for code in required_codes:
            row = expected_by_code.get(_norm(code), {})
            expiry_rules = dict(row.get("expiry_rules") or {})
            requires_expiry = bool(expiry_rules.get("expiry_required") or expiry_rules.get("has_expiry"))
            renewal_window = int(expiry_rules.get("renewal_window_days") or expiring_threshold_for(code, ruleset))

            matches = _docs_for_code(docs, code)
            if not matches:
                missing.append(code)
                gaps.append(code)
                blockers.append(code)
                continue

            present.append(code)
            match_evaluations = [
                evaluate_document_expiry(
                    expires_on=doc.get("expires_at") or doc.get("expire_date"),
                    expiry_required=requires_expiry,
                    reference_date=today,
                    expiring_soon_days=renewal_window,
                )
                for doc in matches
            ]
            evaluations.extend(match_evaluations)
            states = [item.state for item in match_evaluations]

            if any(state == "valid" for state in states):
                continue
            if any(state == "expiring_soon" for state in states):
                picked = next(item for item in match_evaluations if item.state == "expiring_soon")
                expiring_soon.append(
                    {
                        "document_code": code,
                        "expires_on": str(picked.expires_on) if picked.expires_on else None,
                        "days_left": picked.days_left,
                    }
                )
                warnings.append(code)
                continue
            if any(state == "missing_expiry" for state in states):
                missing_expiry.append(code)
                gaps.append(code)
                blockers.append(code)
                continue
            expired.append(code)
            gaps.append(code)
            blockers.append(code)

        packs.append(
            {
                "code": pack.code,
                "label": pack.label,
                "status": _pack_status(gaps=gaps, warnings=warnings, skeleton=False),
                "skeleton": False,
                "applies": True,
                "ref_pack_codes": list(pack.ref_pack_codes),
                "required": required_codes,
                "present": present,
                "missing": missing,
                "expired": expired,
                "expiring_soon": expiring_soon,
                "missing_expiry": missing_expiry,
                "gaps": gaps,
                "blockers": blockers,
                "warnings": warnings,
                "expiry": owner_expiry_aggregate_to_dict(aggregate_document_expiry_states(evaluations)),
            }
        )

    return packs
