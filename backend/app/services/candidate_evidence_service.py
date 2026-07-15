"""Candidate Evidence service — Recruitment confirms requirements via explicit evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_evidence import CandidateEvidence, CandidateEvidenceDocument
from backend.app.models.document import Document
from backend.app.models.enums import CandidateEvidenceStatus
from backend.app.requirement_rules.constants import RULE_TYPE_DOCUMENT_SLOT_REQUIRED
from backend.app.requirement_rules.readiness_bridge import (
    build_normalized_payload_from_candidate,
    load_candidate_documents_snapshot,
    resolve_entity_profile_code_for_candidate,
)
from backend.app.requirement_rules.slot_evaluator import (
    evaluate_document_slot,
    evaluate_slot_alternatives,
    expand_type_codes_for_slot,
)
from backend.app.requirement_rules.slot_registry import get_slot_definition
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.requirement_document_data import (
    enrich_document_snapshot_for_checklist,
    extraction_blockers_for_documents,
    missing_extraction_fields,
)

ACTIVE_EVIDENCE_STATUSES = frozenset(
    {
        CandidateEvidenceStatus.draft.value,
        CandidateEvidenceStatus.selected.value,
        CandidateEvidenceStatus.pending_review.value,
        CandidateEvidenceStatus.approved.value,
    }
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _status_value(row: CandidateEvidence) -> str:
    raw = getattr(row, "status", "")
    if hasattr(raw, "value"):
        return str(raw.value)
    return str(raw or "")


def _variant_codes_for_requirement(requirement_code: str) -> set[str]:
    slot = get_slot_definition(requirement_code)
    if not slot:
        return set()
    out: set[str] = set()
    alts = slot.get("accepted_evidence_variants") or slot.get("satisfaction_alternatives") or []
    for alt in alts:
        if not isinstance(alt, dict):
            continue
        code = _norm(alt.get("evidence_variant_code") or alt.get("alternative_code"))
        if code:
            out.add(code)
    return out


def _variant_definition(requirement_code: str, variant_code: str) -> Optional[dict[str, Any]]:
    slot = get_slot_definition(requirement_code)
    if not slot:
        return None
    target = _norm(variant_code)
    alts = slot.get("accepted_evidence_variants") or slot.get("satisfaction_alternatives") or []
    for alt in alts:
        if not isinstance(alt, dict):
            continue
        code = _norm(alt.get("evidence_variant_code") or alt.get("alternative_code"))
        if code == target:
            return alt
    return None


def _document_type_matches_variant(doc_type: str, variant: dict[str, Any]) -> bool:
    normalized = normalize_doc_type(doc_type)
    allowed: set[str] = set()
    for code in variant.get("document_type_codes") or variant.get("any_of") or []:
        allowed.add(normalize_doc_type(str(code)))
    for code in variant.get("all_of") or []:
        allowed.add(normalize_doc_type(str(code)))
    return normalized in allowed


def _required_type_codes_for_variant(variant: dict[str, Any]) -> set[str]:
    all_of = variant.get("all_of") or []
    if all_of:
        return {normalize_doc_type(str(code)) for code in all_of}
    any_of = variant.get("document_type_codes") or variant.get("any_of") or []
    return {normalize_doc_type(str(code)) for code in any_of}


def _extracted_fields_from_document(doc: Document) -> dict[str, Any]:
    meta = getattr(doc, "meta", None) or {}
    if not isinstance(meta, dict):
        return {}
    extracted = meta.get("extracted_fields") or meta.get("fields") or {}
    return dict(extracted) if isinstance(extracted, dict) else {}


def _enrich_checklist_document_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_document_snapshot_for_checklist(row) for row in snapshots if isinstance(row, dict)]


def _apply_document_data_enrichment_to_evaluation(
    *,
    slot: dict[str, Any],
    evidence_snapshot: dict[str, Any] | None,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(evaluation)
    linked_docs = list((evidence_snapshot or {}).get("documents") or [])
    alternatives = slot.get("accepted_evidence_variants") or slot.get("satisfaction_alternatives") or []
    if len(alternatives) > 1:
        enriched["alternatives_evaluated"] = evaluate_slot_alternatives(slot, linked_docs=linked_docs)

    if linked_docs:
        extraction_blockers = extraction_blockers_for_documents(linked_docs)
        if extraction_blockers:
            enriched["blockers"] = list(enriched.get("blockers") or []) + extraction_blockers
            evidence_status = _norm((evidence_snapshot or {}).get("status"))
            if evidence_status in {"selected", "pending_review"} and enriched.get("status") not in {
                "satisfied",
                "not_applicable",
            }:
                enriched["status"] = "pending_verification"
                enriched["extraction_incomplete"] = True

    return enriched


def _expanded_type_codes(type_code: str) -> set[str]:
    return expand_type_codes_for_slot([_norm(type_code)])


def _linked_types_satisfy_variant(linked_types: set[str], variant: dict[str, Any]) -> bool:
    expanded_linked: set[str] = set()
    for code in linked_types:
        expanded_linked |= _expanded_type_codes(code)

    all_of = variant.get("all_of") or []
    if all_of:
        for code in all_of:
            expanded_required = _expanded_type_codes(str(code))
            if not expanded_linked.intersection(expanded_required):
                return False
        return True

    any_of = variant.get("document_type_codes") or variant.get("any_of") or []
    expanded_allowed: set[str] = set()
    for code in any_of:
        expanded_allowed |= _expanded_type_codes(str(code))
    return bool(expanded_linked.intersection(expanded_allowed))


async def _load_linked_document_rows(
    db: AsyncSession,
    *,
    tenant_id: str,
    evidence_id: str,
) -> list[tuple[CandidateEvidenceDocument, Document | None]]:
    stmt = (
        select(CandidateEvidenceDocument, Document)
        .outerjoin(Document, Document.id == CandidateEvidenceDocument.document_id)
        .where(CandidateEvidenceDocument.tenant_id == str(tenant_id))
        .where(CandidateEvidenceDocument.candidate_evidence_id == str(evidence_id))
    )
    return list((await db.execute(stmt)).all())


async def _get_candidate_or_404(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
) -> Candidate:
    row = await db.get(Candidate, str(candidate_id))
    if not row or str(row.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return row


async def _get_evidence_or_404(
    db: AsyncSession,
    tenant_id: str,
    evidence_id: str,
    *,
    candidate_id: str | None = None,
) -> CandidateEvidence:
    stmt = (
        select(CandidateEvidence)
        .where(CandidateEvidence.id == str(evidence_id))
        .where(CandidateEvidence.tenant_id == str(tenant_id))
        .options(selectinload(CandidateEvidence.documents).selectinload(CandidateEvidenceDocument.document))
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate evidence not found")
    if candidate_id and str(row.candidate_id) != str(candidate_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate evidence not found")
    return row


async def get_active_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    requirement_code: str,
) -> Optional[CandidateEvidence]:
    stmt = (
        select(CandidateEvidence)
        .where(CandidateEvidence.tenant_id == str(tenant_id))
        .where(CandidateEvidence.candidate_id == str(candidate_id))
        .where(CandidateEvidence.requirement_code == _norm(requirement_code))
        .where(CandidateEvidence.status.in_(sorted(ACTIVE_EVIDENCE_STATUSES)))
        .order_by(CandidateEvidence.updated_at.desc())
        .options(selectinload(CandidateEvidence.documents).selectinload(CandidateEvidenceDocument.document))
    )
    return (await db.execute(stmt)).scalars().first()


async def list_evidence_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    include_superseded: bool = False,
) -> list[CandidateEvidence]:
    stmt = (
        select(CandidateEvidence)
        .where(CandidateEvidence.tenant_id == str(tenant_id))
        .where(CandidateEvidence.candidate_id == str(candidate_id))
        .order_by(CandidateEvidence.updated_at.desc())
        .options(selectinload(CandidateEvidence.documents).selectinload(CandidateEvidenceDocument.document))
    )
    if not include_superseded:
        stmt = stmt.where(
            CandidateEvidence.status.notin_(
                [
                    CandidateEvidenceStatus.superseded.value,
                ]
            )
        )
    return list((await db.execute(stmt)).scalars().all())


async def load_candidate_evidence_snapshots(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> dict[str, dict[str, Any]]:
    """Active evidence keyed by requirement_code for requirement engine evaluation."""
    rows = await list_evidence_for_candidate(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        include_superseded=False,
    )
    doc_snapshots = {
        str(row.get("document_id") or row.get("id")): row
        for row in await load_candidate_documents_snapshot(db, tenant_id=tenant_id, candidate_id=candidate_id)
    }
    out: dict[str, dict[str, Any]] = {}
    for evidence in rows:
        req_code = _norm(evidence.requirement_code)
        if req_code in out:
            continue
        linked_docs: list[dict[str, Any]] = []
        for junction in evidence.documents or []:
            doc = junction.document
            if doc is None:
                snap = doc_snapshots.get(str(junction.document_id))
                if snap:
                    linked_docs.append(snap)
                continue
            snap = doc_snapshots.get(str(doc.id))
            linked_docs.append(
                snap
                if snap
                else {
                    "document_id": str(doc.id),
                    "document_type_code": normalize_doc_type(getattr(doc, "doc_type", "") or ""),
                    "type": normalize_doc_type(getattr(doc, "doc_type", "") or ""),
                    "status": getattr(doc, "status", None),
                    "has_files": bool(getattr(doc, "files", None)),
                    "expire_date": getattr(doc, "expire_date", None),
                }
            )
        out[req_code] = serialize_candidate_evidence(evidence, linked_docs)
    return out


def serialize_candidate_evidence(
    evidence: CandidateEvidence,
    linked_document_snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    docs = list(linked_document_snapshots or [])
    return {
        "evidence_id": str(evidence.id),
        "requirement_code": _norm(evidence.requirement_code),
        "evidence_variant_code": _norm(evidence.evidence_variant_code),
        "status": _status_value(evidence),
        "selected_by": str(evidence.selected_by) if evidence.selected_by else None,
        "selected_at": evidence.selected_at.isoformat() if evidence.selected_at else None,
        "approved_by": str(evidence.approved_by) if evidence.approved_by else None,
        "approved_at": evidence.approved_at.isoformat() if evidence.approved_at else None,
        "rejected_by": str(evidence.rejected_by) if evidence.rejected_by else None,
        "rejected_at": evidence.rejected_at.isoformat() if evidence.rejected_at else None,
        "rejection_reason": evidence.rejection_reason,
        "documents": docs,
    }


async def supersede_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    evidence: CandidateEvidence,
    user_id: str,
    replacement_evidence_id: str | None = None,
) -> CandidateEvidence:
    evidence.status = CandidateEvidenceStatus.superseded.value
    evidence.superseded_by = str(user_id)
    evidence.superseded_at = _now()
    evidence.superseded_by_evidence_id = str(replacement_evidence_id) if replacement_evidence_id else None
    evidence.updated_at = _now()
    await db.flush()
    return evidence


async def select_evidence_variant(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    requirement_code: str,
    evidence_variant_code: str,
    user_id: str,
) -> CandidateEvidence:
    await _get_candidate_or_404(db, tenant_id, candidate_id)
    req_code = _norm(requirement_code)
    variant_code = _norm(evidence_variant_code)
    if variant_code not in _variant_codes_for_requirement(req_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown evidence variant {variant_code} for requirement {req_code}",
        )

    existing = await get_active_evidence(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        requirement_code=req_code,
    )
    replacement_id: str | None = None
    if existing:
        if (
            _norm(existing.evidence_variant_code) == variant_code
            and _status_value(existing) != CandidateEvidenceStatus.superseded.value
        ):
            return existing
        row = CandidateEvidence(
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            requirement_code=req_code,
            evidence_variant_code=variant_code,
            status=CandidateEvidenceStatus.selected.value,
            selected_by=str(user_id),
            selected_at=_now(),
        )
        db.add(row)
        await db.flush()
        replacement_id = str(row.id)
        await supersede_evidence(
            db,
            tenant_id=tenant_id,
            evidence=existing,
            user_id=user_id,
            replacement_evidence_id=replacement_id,
        )
        return row

    row = CandidateEvidence(
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        requirement_code=req_code,
        evidence_variant_code=variant_code,
        status=CandidateEvidenceStatus.selected.value,
        selected_by=str(user_id),
        selected_at=_now(),
    )
    db.add(row)
    await db.flush()
    return row


async def link_document_to_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    evidence_id: str,
    document_id: str,
    user_id: str,
    role: str | None = None,
) -> CandidateEvidenceDocument:
    evidence = await _get_evidence_or_404(db, tenant_id, evidence_id)
    if _status_value(evidence) in {
        CandidateEvidenceStatus.approved.value,
        CandidateEvidenceStatus.superseded.value,
        CandidateEvidenceStatus.rejected.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot link documents to evidence in status {_status_value(evidence)}",
        )

    doc = await db.get(Document, str(document_id))
    if not doc or str(doc.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if str(doc.candidate_id) != str(evidence.candidate_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document does not belong to this candidate",
        )

    variant = _variant_definition(evidence.requirement_code, evidence.evidence_variant_code)
    if variant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid evidence variant")
    if not _document_type_matches_variant(getattr(doc, "doc_type", "") or "", variant):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type does not match selected evidence variant",
        )

    for junction in evidence.documents or []:
        if str(junction.document_id) == str(document_id):
            return junction

    junction = CandidateEvidenceDocument(
        tenant_id=str(tenant_id),
        candidate_evidence_id=str(evidence.id),
        document_id=str(document_id),
        role=role,
        linked_by=str(user_id),
    )
    db.add(junction)
    evidence.updated_at = _now()
    if _status_value(evidence) == CandidateEvidenceStatus.selected.value:
        evidence.status = CandidateEvidenceStatus.pending_review.value
    await db.flush()
    return junction


async def _validate_evidence_ready_for_approval(
    db: AsyncSession,
    *,
    tenant_id: str,
    evidence: CandidateEvidence,
) -> None:
    variant = _variant_definition(evidence.requirement_code, evidence.evidence_variant_code)
    if variant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid evidence variant")

    linked_types: set[str] = set()
    linked_rows = await _load_linked_document_rows(
        db,
        tenant_id=str(tenant_id),
        evidence_id=str(evidence.id),
    )
    if not linked_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No linked document satisfies selected evidence variant",
        )

    for junction, doc in linked_rows:
        if doc is None:
            doc = await db.get(Document, str(junction.document_id))
        if doc is None:
            continue
        linked_types.add(normalize_doc_type(getattr(doc, "doc_type", "") or ""))

    if not _linked_types_satisfy_variant(linked_types, variant):
        if variant.get("all_of"):
            missing = {
                normalize_doc_type(str(code))
                for code in (variant.get("all_of") or [])
            } - linked_types
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing linked documents for types: {', '.join(sorted(missing))}",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No linked document satisfies selected evidence variant",
        )

    candidate = await db.get(Candidate, str(evidence.candidate_id))
    payload = build_normalized_payload_from_candidate(candidate) if candidate else {}
    citizenship = payload.get("citizenship") or payload.get("platform.identity.citizenship")
    snapshots = await load_candidate_documents_snapshot(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(evidence.candidate_id),
    )
    linked_ids = {str(junction.document_id) for junction, _doc in linked_rows}
    linked_snapshots = [row for row in snapshots if str(row.get("document_id") or row.get("id")) in linked_ids]
    if not linked_snapshots and linked_rows:
        linked_snapshots = []
        for junction, doc in linked_rows:
            if doc is None:
                continue
            linked_snapshots.append(
                enrich_document_snapshot_for_checklist(
                    {
                        "document_id": str(doc.id),
                        "document_type_code": normalize_doc_type(getattr(doc, "doc_type", "") or ""),
                        "type": normalize_doc_type(getattr(doc, "doc_type", "") or ""),
                        "status": getattr(doc.status, "value", getattr(doc, "status", "")),
                        "has_files": bool(getattr(doc, "files", None)),
                        "expire_date": getattr(doc, "expire_date", None),
                        "meta": getattr(doc, "meta", None) or {},
                    }
                )
            )
    else:
        linked_snapshots = _enrich_checklist_document_snapshots(linked_snapshots)

    for snapshot in linked_snapshots:
        if missing_extraction_fields(snapshot):
            missing = ", ".join(snapshot.get("missing_extraction_fields") or [])
            doc_type = snapshot.get("document_type_code") or snapshot.get("type") or "document"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing extraction fields on {doc_type}: {missing}",
            )

    evaluation = evaluate_document_slot(
        evidence.requirement_code,
        candidate_evidence={
            **serialize_candidate_evidence(evidence, linked_snapshots),
            "status": CandidateEvidenceStatus.approved.value,
        },
        citizenship=str(citizenship).strip() if citizenship else None,
    )
    if evaluation.get("status") != "satisfied":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linked documents are not valid for this requirement",
        )


async def approve_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    evidence_id: str,
    user_id: str,
) -> CandidateEvidence:
    evidence = await _get_evidence_or_404(db, tenant_id, evidence_id)
    if _status_value(evidence) == CandidateEvidenceStatus.approved.value:
        return evidence
    if _status_value(evidence) in {
        CandidateEvidenceStatus.superseded.value,
        CandidateEvidenceStatus.rejected.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve evidence in status {_status_value(evidence)}",
        )

    await _validate_evidence_ready_for_approval(db, tenant_id=tenant_id, evidence=evidence)
    evidence.status = CandidateEvidenceStatus.approved.value
    evidence.approved_by = str(user_id)
    evidence.approved_at = _now()
    evidence.updated_at = _now()
    await db.flush()
    return evidence


async def reject_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    evidence_id: str,
    user_id: str,
    reason: str | None = None,
) -> CandidateEvidence:
    evidence = await _get_evidence_or_404(db, tenant_id, evidence_id)
    if _status_value(evidence) in {
        CandidateEvidenceStatus.approved.value,
        CandidateEvidenceStatus.superseded.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject evidence in status {_status_value(evidence)}",
        )
    evidence.status = CandidateEvidenceStatus.rejected.value
    evidence.rejected_by = str(user_id)
    evidence.rejected_at = _now()
    evidence.rejection_reason = (reason or "").strip() or None
    evidence.updated_at = _now()
    await db.flush()
    return evidence


async def replace_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    requirement_code: str,
    evidence_variant_code: str,
    user_id: str,
) -> CandidateEvidence:
    """Replace active evidence with a fresh row; always supersedes the previous active row."""
    await _get_candidate_or_404(db, tenant_id, candidate_id)
    req_code = _norm(requirement_code)
    variant_code = _norm(evidence_variant_code)
    if variant_code not in _variant_codes_for_requirement(req_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown evidence variant {variant_code} for requirement {req_code}",
        )

    existing = await get_active_evidence(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        requirement_code=req_code,
    )
    row = CandidateEvidence(
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        requirement_code=req_code,
        evidence_variant_code=variant_code,
        status=CandidateEvidenceStatus.selected.value,
        selected_by=str(user_id),
        selected_at=_now(),
    )
    db.add(row)
    await db.flush()
    if existing and str(existing.id) != str(row.id):
        await supersede_evidence(
            db,
            tenant_id=tenant_id,
            evidence=existing,
            user_id=user_id,
            replacement_evidence_id=str(row.id),
        )
    return row


async def resolve_required_requirement_codes(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> list[str]:
    entity_profile_code = await resolve_entity_profile_code_for_candidate(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
    )
    if not entity_profile_code:
        return []
    from backend.app.requirement_rules.facade import resolve_requirement_rule_set

    rule_set = await resolve_requirement_rule_set(
        db,
        tenant_id=str(tenant_id),
        entity_profile_code=entity_profile_code,
        context="readiness",
    )
    codes: list[str] = []
    for rule in rule_set.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        if str(rule.get("rule_type") or "") != RULE_TYPE_DOCUMENT_SLOT_REQUIRED:
            continue
        code = _norm(rule.get("slot_code") or rule.get("target") or rule.get("requirement_code"))
        if code:
            codes.append(code)
    return codes


def map_requirements_checklist_to_pipeline_blockers(
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Map requirement checklist rows to pipeline blocker lists (requirement codes, not doc types)."""
    missing: list[str] = []
    problematic: list[str] = []
    pending_review: list[str] = []
    unfulfilled: list[dict[str, Any]] = []

    for item in requirements or []:
        if not isinstance(item, dict):
            continue
        evaluation = item.get("evaluation") if isinstance(item.get("evaluation"), dict) else {}
        eval_status = _norm(str(evaluation.get("status") or ""))
        if eval_status == "not_applicable" or item.get("fulfilled"):
            continue

        req_code = _norm(str(item.get("requirement_code") or ""))
        if not req_code:
            continue

        evidence = item.get("candidate_evidence") if isinstance(item.get("candidate_evidence"), dict) else {}
        evidence_status = _norm(str(evidence.get("status") or ""))

        row = {
            "requirement_code": req_code,
            "public_name": item.get("public_name"),
            "evaluation_status": eval_status or None,
            "evidence_status": evidence_status or None,
            "fulfilled": False,
        }
        unfulfilled.append(row)

        if evidence_status == "rejected":
            problematic.append(req_code)
        elif eval_status == "pending_verification" or evidence_status == "pending_review":
            pending_review.append(req_code)
        else:
            missing.append(req_code)

    return {
        "source": "requirement_fulfillment_v1",
        "all_fulfilled": not unfulfilled,
        "missing_requirements": missing,
        "problematic_requirements": problematic,
        "pending_review_requirements": pending_review,
        "unfulfilled_requirements": unfulfilled,
    }


async def build_requirements_checklist(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> dict[str, Any]:
    requirement_codes = await resolve_required_requirement_codes(db, tenant_id=tenant_id, candidate=candidate)
    payload = build_normalized_payload_from_candidate(candidate)
    citizenship = payload.get("citizenship") or payload.get("platform.identity.citizenship")
    position_category = payload.get("position_category")

    items: list[dict[str, Any]] = []
    for req_code in requirement_codes:
        slot = get_slot_definition(req_code) or {}
        evidence_row = await get_active_evidence(
            db,
            tenant_id=str(tenant_id),
            candidate_id=str(candidate.id),
            requirement_code=req_code,
        )
        evidence_snapshot = None
        if evidence_row:
            snapshots = await load_candidate_documents_snapshot(
                db,
                tenant_id=str(tenant_id),
                candidate_id=str(candidate.id),
            )
            linked_ids = {str(j.document_id) for j in evidence_row.documents or []}
            linked_snapshots = [
                row for row in snapshots if str(row.get("document_id") or row.get("id")) in linked_ids
            ]
            linked_snapshots = _enrich_checklist_document_snapshots(linked_snapshots)
            evidence_snapshot = serialize_candidate_evidence(evidence_row, linked_snapshots)

        evaluation = evaluate_document_slot(
            req_code,
            candidate_evidence=evidence_snapshot,
            citizenship=str(citizenship).strip() if citizenship else None,
            position_category=str(position_category).strip() if position_category else None,
        )
        evaluation = _apply_document_data_enrichment_to_evaluation(
            slot=slot,
            evidence_snapshot=evidence_snapshot,
            evaluation=evaluation,
        )
        variants = []
        for alt in slot.get("accepted_evidence_variants") or slot.get("satisfaction_alternatives") or []:
            if not isinstance(alt, dict):
                continue
            variants.append(
                {
                    "evidence_variant_code": _norm(
                        alt.get("evidence_variant_code") or alt.get("alternative_code")
                    ),
                    "document_type_codes": alt.get("document_type_codes")
                    or alt.get("any_of")
                    or alt.get("all_of")
                    or [],
                    "all_of": bool(alt.get("all_of")),
                }
            )
        eval_status = evaluation.get("status")
        items.append(
            {
                "requirement_code": req_code,
                "public_name": slot.get("public_name"),
                "business_purpose": slot.get("business_purpose"),
                "level": slot.get("level") or "blocking",
                "accepted_evidence_variants": variants,
                "candidate_evidence": evidence_snapshot,
                "evaluation": evaluation,
                "fulfilled": eval_status in {"satisfied", "not_applicable"},
            }
        )

    pipeline_blockers = map_requirements_checklist_to_pipeline_blockers(items)

    return {
        "candidate_id": str(candidate.id),
        "requirements": items,
        "all_fulfilled": all(item["fulfilled"] or item["evaluation"].get("status") == "not_applicable" for item in items),
        "pipeline_blockers": pipeline_blockers,
    }


def build_requirements_work_panel_preview(checklist: dict[str, Any]) -> dict[str, Any]:
    """Compact requirement rows for Candidates work-panel preview."""
    rows: list[dict[str, Any]] = []
    for item in checklist.get("requirements") or []:
        if not isinstance(item, dict):
            continue
        evidence = item.get("candidate_evidence") if isinstance(item.get("candidate_evidence"), dict) else {}
        docs = evidence.get("documents") or []
        linked: dict[str, Any] | None = None
        if docs and isinstance(docs[0], dict):
            d = docs[0]
            linked = {
                "document_id": d.get("document_id") or d.get("id"),
                "document_type_code": d.get("document_type_code") or d.get("type"),
                "status": d.get("status"),
            }
        evaluation = item.get("evaluation") if isinstance(item.get("evaluation"), dict) else {}
        rows.append(
            {
                "requirement_code": item.get("requirement_code"),
                "public_name": item.get("public_name"),
                "fulfilled": bool(item.get("fulfilled")),
                "evaluation_status": evaluation.get("status"),
                "evidence_variant_code": evidence.get("evidence_variant_code"),
                "evidence_status": evidence.get("status"),
                "linked_document": linked,
            }
        )
    pb = checklist.get("pipeline_blockers")
    return {
        "all_fulfilled": bool(checklist.get("all_fulfilled")),
        "pipeline_blockers": pb if isinstance(pb, dict) else {},
        "items": rows,
    }


async def build_requirement_fulfillments_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> list[dict[str, Any]]:
    """Approved Candidate Evidence rows for handoff payload."""
    stmt = (
        select(CandidateEvidence)
        .where(CandidateEvidence.tenant_id == str(tenant_id))
        .where(CandidateEvidence.candidate_id == str(candidate_id))
        .where(CandidateEvidence.status == CandidateEvidenceStatus.approved.value)
        .options(selectinload(CandidateEvidence.documents).selectinload(CandidateEvidenceDocument.document))
        .order_by(CandidateEvidence.requirement_code.asc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    fulfillments: list[dict[str, Any]] = []
    for evidence in rows:
        slot = get_slot_definition(evidence.requirement_code) or {}
        documents_out: list[dict[str, Any]] = []
        for junction in evidence.documents or []:
            doc = junction.document or await db.get(Document, str(junction.document_id))
            if doc is None:
                continue
            documents_out.append(
                {
                    "document_id": str(doc.id),
                    "document_type_code": normalize_doc_type(getattr(doc, "doc_type", "") or ""),
                    "role": junction.role,
                    "expires_at": doc.expire_date.isoformat() if getattr(doc, "expire_date", None) else None,
                    "extracted_fields": _extracted_fields_from_document(doc),
                }
            )
        fulfillments.append(
            {
                "requirement_code": _norm(evidence.requirement_code),
                "requirement_public_name": slot.get("public_name"),
                "business_purpose": slot.get("business_purpose"),
                "evidence_id": str(evidence.id),
                "evidence_variant_code": _norm(evidence.evidence_variant_code),
                "approved_at": evidence.approved_at.isoformat() if evidence.approved_at else None,
                "approved_by": str(evidence.approved_by) if evidence.approved_by else None,
                "documents": documents_out,
            }
        )
    return fulfillments
