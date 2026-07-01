"""Evaluate requirement satisfaction via Candidate Evidence (ADR-016 Phase 2)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.document_runtime.evaluator import evaluate_document_runtime
from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS
from backend.app.requirement_rules.slot_registry import get_slot_definition, slot_applies


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _document_type_code(doc: dict[str, Any]) -> str:
    for key in ("document_type_code", "type", "type_code", "doc_type"):
        raw = doc.get(key)
        if raw is not None and str(raw).strip():
            return _norm(raw)
    return ""


def _expand_type_codes(type_codes: list[str]) -> set[str]:
    """Expand to module catalog code + aliases for each requested type only."""
    targets = {_norm(c) for c in type_codes if _norm(c)}
    if not targets:
        return set()

    expanded: set[str] = set()
    for definition in DOCUMENT_TYPE_DEFINITIONS:
        def_codes = {_norm(definition.code)}
        def_codes.update(_norm(a) for a in definition.aliases)
        if targets.intersection(def_codes):
            expanded.update(def_codes)

    return expanded or set(targets)


def _index_documents(documents: list[Any]) -> dict[str, dict[str, Any]]:
    """Best instance per document type string from an explicit document list."""
    index: dict[str, dict[str, Any]] = {}
    for raw in documents or []:
        if not isinstance(raw, dict):
            continue
        code = _document_type_code(raw)
        if not code:
            continue
        runtime = raw.get("document_runtime")
        if not isinstance(runtime, dict):
            runtime = evaluate_document_runtime(raw, document_type_code=code)
        row = {**raw, "document_runtime": runtime}
        for key in _expand_type_codes([code]) | {code}:
            existing = index.get(key)
            if existing is None:
                index[key] = row
                continue
            existing_runtime = existing.get("document_runtime") or {}
            if bool(runtime.get("satisfies_requirement")) and not bool(
                existing_runtime.get("satisfies_requirement")
            ):
                index[key] = row
    return index


def _type_satisfaction(
    type_code: str,
    doc_index: dict[str, dict[str, Any]],
) -> tuple[str, Optional[dict[str, Any]]]:
    """Return (status, doc) where status is satisfied | pending | missing."""
    expanded = _expand_type_codes([type_code])
    best_pending: Optional[dict[str, Any]] = None
    for key, doc in doc_index.items():
        if key not in expanded:
            continue
        runtime = doc.get("document_runtime") or evaluate_document_runtime(doc, document_type_code=key)
        if runtime.get("satisfies_requirement"):
            return "satisfied", doc
        best_pending = doc
    if best_pending is not None:
        return "pending", best_pending
    return "missing", None


def _alternative_status(
    alternative: dict[str, Any],
    *,
    doc_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    alt_code = _norm(
        alternative.get("evidence_variant_code")
        or alternative.get("alternative_code")
        or "default"
    )
    any_of = [
        _norm(x)
        for x in (alternative.get("document_type_codes") or alternative.get("any_of") or [])
        if _norm(x)
    ]
    all_of = [
        _norm(x)
        for x in (alternative.get("all_of") or [])
        if _norm(x)
    ]

    if any_of:
        present_types: list[str] = []
        satisfied_types: list[str] = []
        satisfying_ids: list[str] = []
        has_pending = False
        for code in any_of:
            status, doc = _type_satisfaction(code, doc_index)
            if status == "satisfied" and doc:
                satisfied_types.append(code)
                raw_id = doc.get("document_id") or doc.get("id")
                if raw_id:
                    satisfying_ids.append(str(raw_id))
            elif status == "pending":
                present_types.append(code)
                has_pending = True
        if satisfied_types:
            return {
                "alternative_code": alt_code,
                "evidence_variant_code": alt_code,
                "status": "satisfied",
                "satisfying_document_ids": satisfying_ids,
                "document_type_codes": satisfied_types,
            }
        if has_pending:
            return {
                "alternative_code": alt_code,
                "evidence_variant_code": alt_code,
                "status": "pending_verification",
                "satisfying_document_ids": [],
                "document_type_codes": present_types,
                "partial": True,
            }
        return {
            "alternative_code": alt_code,
            "evidence_variant_code": alt_code,
            "status": "missing",
            "satisfying_document_ids": [],
            "document_type_codes": [],
        }

    if all_of:
        satisfied_types: list[str] = []
        satisfying_ids: list[str] = []
        has_pending = False
        for code in all_of:
            status, doc = _type_satisfaction(code, doc_index)
            if status != "satisfied" or not doc:
                if status == "pending":
                    has_pending = True
                return {
                    "alternative_code": alt_code,
                    "evidence_variant_code": alt_code,
                    "status": "pending_verification" if has_pending else "missing",
                    "satisfying_document_ids": [],
                    "document_type_codes": satisfied_types,
                    "partial": has_pending or bool(satisfied_types),
                }
            satisfied_types.append(code)
            raw_id = doc.get("document_id") or doc.get("id")
            if raw_id:
                satisfying_ids.append(str(raw_id))
        return {
            "alternative_code": alt_code,
            "evidence_variant_code": alt_code,
            "status": "satisfied",
            "satisfying_document_ids": satisfying_ids,
            "document_type_codes": satisfied_types,
        }

    return {
        "alternative_code": alt_code,
        "evidence_variant_code": alt_code,
        "status": "missing",
        "satisfying_document_ids": [],
        "document_type_codes": [],
    }


def _find_variant_definition(slot: dict[str, Any], variant_code: str) -> Optional[dict[str, Any]]:
    target = _norm(variant_code)
    alts = slot.get("accepted_evidence_variants") or slot.get("satisfaction_alternatives") or []
    for alt in alts:
        if not isinstance(alt, dict):
            continue
        code = _norm(alt.get("evidence_variant_code") or alt.get("alternative_code"))
        if code == target:
            return alt
    return None


def _evidence_documents(candidate_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    docs = candidate_evidence.get("documents")
    if isinstance(docs, list):
        return [row for row in docs if isinstance(row, dict)]
    return []


def _base_slot_result(
    slot: dict[str, Any],
    *,
    code: str,
    level: str,
    status: str,
    blockers: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "slot_code": code,
        "requirement_code": code,
        "status": status,
        "level": level,
        "business_purpose": slot.get("business_purpose"),
        "public_name": slot.get("public_name"),
        "satisfaction_alternatives": slot.get("accepted_evidence_variants")
        or slot.get("satisfaction_alternatives")
        or [],
        "alternatives_evaluated": [],
        "blockers": blockers or [],
        **extra,
    }


def evaluate_document_slot(
    slot_code: str,
    *,
    documents: list[Any] | None = None,
    candidate_evidence: Optional[dict[str, Any]] = None,
    citizenship: Optional[str] = None,
    position_category: Optional[str] = None,
    require_explicit_choice: bool = False,
) -> dict[str, Any]:
    """Evaluate one requirement against Candidate Evidence (no document-type guessing)."""
    slot = get_slot_definition(slot_code)
    if slot is None:
        return {
            "slot_code": _norm(slot_code),
            "requirement_code": _norm(slot_code),
            "status": "unknown",
            "level": "blocking",
            "blockers": [{"code": "unknown_slot", "message": f"Unknown requirement: {slot_code}"}],
        }

    code = _norm(slot.get("requirement_code") or slot.get("slot_code"))
    level = _norm(slot.get("level") or "blocking") or "blocking"
    if not slot_applies(slot, citizenship=citizenship, position_category=position_category):
        return _base_slot_result(slot, code=code, level=level, status="not_applicable")

    if not candidate_evidence:
        return _base_slot_result(
            slot,
            code=code,
            level=level,
            status="missing",
            blockers=[
                {
                    "code": f"candidate_evidence_required:{code}",
                    "message": f"Requirement {code} requires explicit Candidate Evidence selection",
                    "slot_code": code,
                    "requirement_code": code,
                    "layer": "candidate_evidence",
                }
            ]
            if level == "blocking"
            else [],
        )

    evidence_status = _norm(candidate_evidence.get("status"))
    variant_code = _norm(candidate_evidence.get("evidence_variant_code"))
    linked_docs = _evidence_documents(candidate_evidence)
    if not linked_docs and documents:
        linked_docs = [row for row in documents if isinstance(row, dict)]

    if evidence_status == "rejected":
        return _base_slot_result(
            slot,
            code=code,
            level=level,
            status="missing",
            evidence_status=evidence_status,
            evidence_variant_code=variant_code or None,
            blockers=[
                {
                    "code": f"candidate_evidence_rejected:{code}",
                    "message": f"Candidate evidence for {code} was rejected",
                    "slot_code": code,
                    "requirement_code": code,
                    "layer": "candidate_evidence",
                }
            ]
            if level == "blocking"
            else [],
        )

    if evidence_status in {"draft", "selected"}:
        return _base_slot_result(
            slot,
            code=code,
            level=level,
            status="pending_evidence",
            evidence_status=evidence_status,
            evidence_variant_code=variant_code or None,
            blockers=[
                {
                    "code": f"candidate_evidence_incomplete:{code}",
                    "message": f"Candidate evidence for {code} is not submitted for review",
                    "slot_code": code,
                    "requirement_code": code,
                    "layer": "candidate_evidence",
                }
            ]
            if level == "blocking"
            else [],
        )

    if evidence_status == "pending_review":
        variant = _find_variant_definition(slot, variant_code) if variant_code else None
        if variant is None:
            return _base_slot_result(
                slot,
                code=code,
                level=level,
                status="missing",
                evidence_status=evidence_status,
                blockers=[
                    {
                        "code": f"candidate_evidence_invalid_variant:{code}",
                        "message": f"Unknown evidence variant for {code}: {variant_code}",
                        "slot_code": code,
                        "requirement_code": code,
                        "layer": "candidate_evidence",
                    }
                ],
            )
        evaluated = _alternative_status(variant, doc_index=_index_documents(linked_docs))
        return _base_slot_result(
            slot,
            code=code,
            level=level,
            status="pending_verification",
            evidence_status=evidence_status,
            evidence_variant_code=variant_code,
            chosen_alternative_code=evaluated.get("alternative_code"),
            chosen_document_type_codes=evaluated.get("document_type_codes") or [],
            satisfying_document_ids=evaluated.get("satisfying_document_ids") or [],
            alternatives_evaluated=[evaluated],
            blockers=[
                {
                    "code": f"candidate_evidence_pending_review:{code}",
                    "message": f"Candidate evidence for {code} awaits approval",
                    "slot_code": code,
                    "requirement_code": code,
                    "layer": "candidate_evidence",
                }
            ]
            if level == "blocking"
            else [],
        )

    if evidence_status != "approved":
        return _base_slot_result(
            slot,
            code=code,
            level=level,
            status="missing",
            evidence_status=evidence_status,
            blockers=[
                {
                    "code": f"candidate_evidence_inactive:{code}",
                    "message": f"Candidate evidence for {code} is not active ({evidence_status})",
                    "slot_code": code,
                    "requirement_code": code,
                    "layer": "candidate_evidence",
                }
            ]
            if level == "blocking"
            else [],
        )

    variant = _find_variant_definition(slot, variant_code) if variant_code else None
    if variant is None:
        return _base_slot_result(
            slot,
            code=code,
            level=level,
            status="missing",
            evidence_status=evidence_status,
            blockers=[
                {
                    "code": f"candidate_evidence_invalid_variant:{code}",
                    "message": f"Unknown evidence variant for {code}: {variant_code}",
                    "slot_code": code,
                    "requirement_code": code,
                    "layer": "candidate_evidence",
                }
            ],
        )

    evaluated = _alternative_status(variant, doc_index=_index_documents(linked_docs))
    if evaluated.get("status") == "satisfied":
        return _base_slot_result(
            slot,
            code=code,
            level=level,
            status="satisfied",
            evidence_status=evidence_status,
            evidence_variant_code=variant_code,
            chosen_alternative_code=evaluated.get("alternative_code"),
            chosen_document_type_codes=evaluated.get("document_type_codes") or [],
            satisfying_document_ids=evaluated.get("satisfying_document_ids") or [],
            alternatives_evaluated=[evaluated],
        )

    return _base_slot_result(
        slot,
        code=code,
        level=level,
        status="pending_verification" if evaluated.get("partial") else "missing",
        evidence_status=evidence_status,
        evidence_variant_code=variant_code,
        chosen_alternative_code=evaluated.get("alternative_code"),
        chosen_document_type_codes=evaluated.get("document_type_codes") or [],
        satisfying_document_ids=evaluated.get("satisfying_document_ids") or [],
        alternatives_evaluated=[evaluated],
        blockers=[
            {
                "code": f"candidate_evidence_documents_invalid:{code}",
                "message": f"Linked documents do not satisfy approved evidence for {code}",
                "slot_code": code,
                "requirement_code": code,
                "layer": "candidate_evidence",
            }
        ]
        if level == "blocking"
        else [],
    )


def evaluate_document_slots(
    slot_codes: list[str],
    *,
    documents: list[Any] | None = None,
    candidate_evidence_by_requirement: Optional[dict[str, dict[str, Any]]] = None,
    citizenship: Optional[str] = None,
    position_category: Optional[str] = None,
    require_explicit_choice: bool = False,
) -> dict[str, Any]:
    """Evaluate multiple requirements via Candidate Evidence."""
    evidence_map = candidate_evidence_by_requirement or {}
    rows = [
        evaluate_document_slot(
            code,
            documents=documents,
            candidate_evidence=evidence_map.get(_norm(code)),
            citizenship=citizenship,
            position_category=position_category,
            require_explicit_choice=require_explicit_choice,
        )
        for code in slot_codes
        if _norm(code)
    ]
    blockers: list[dict[str, Any]] = []
    missing_slots: list[str] = []
    for row in rows:
        status = str(row.get("status") or "")
        if status in {
            "missing",
            "needs_alternative_selection",
            "pending_verification",
            "pending_evidence",
        } and row.get("level") == "blocking":
            missing_slots.append(str(row.get("slot_code") or ""))
        blockers.extend(row.get("blockers") or [])

    return {
        "evaluation_version": "candidate_evidence_v1",
        "slots": rows,
        "missing_slots": [s for s in missing_slots if s],
        "satisfied": len(blockers) == 0,
        "blockers": blockers,
    }


def document_types_covered_by_slot(slot_code: str) -> set[str]:
    """All document type codes referenced by a requirement's evidence variants."""
    slot = get_slot_definition(slot_code)
    if not slot:
        return set()
    out: set[str] = set()
    alts = slot.get("accepted_evidence_variants") or slot.get("satisfaction_alternatives") or []
    for alt in alts:
        if not isinstance(alt, dict):
            continue
        for code in alt.get("document_type_codes") or alt.get("any_of") or []:
            out.add(_norm(code))
        for code in alt.get("all_of") or []:
            out.add(_norm(code))
    return out


__all__ = [
    "document_types_covered_by_slot",
    "evaluate_document_slot",
    "evaluate_document_slots",
    "expand_type_codes_for_slot",
]

expand_type_codes_for_slot = _expand_type_codes
