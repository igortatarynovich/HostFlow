from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_pipeline_override import CandidatePipelineOverride
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.hiring_pipeline_gates import resolve_hiring_pipeline_gates
from backend.app.services.pipeline_override_policy import (
    NON_OVERRIDABLE_REQUIREMENT_CODES,
    SCOPE_BOTH,
    SCOPE_PIPELINE,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_REVOKED,
    VALID_GRANTED_SCOPES,
    VALID_REQUESTED_SCOPES,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def row_to_dict(row: CandidatePipelineOverride) -> Dict[str, Any]:
    return {
        "id": row.id,
        "doc_type_code": row.doc_type_code,
        "requirement_code": row.requirement_code,
        "status": row.status,
        "requested_scope": row.requested_scope,
        "granted_scope": row.granted_scope,
        "reason": row.reason,
        "review_note": row.review_note,
        "requested_by_user_id": row.requested_by_user_id,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _norm_requirement_code(value: Optional[str]) -> str:
    return str(value or "").strip().lower().replace("-", "_")


async def list_overrides(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> List[Dict[str, Any]]:
    res = await db.execute(
        select(CandidatePipelineOverride)
        .where(
            CandidatePipelineOverride.tenant_id == tenant_id,
            CandidatePipelineOverride.candidate_id == candidate_id,
        )
        .order_by(CandidatePipelineOverride.created_at.desc())
    )
    rows: Sequence[CandidatePipelineOverride] = res.scalars().all()
    return [row_to_dict(r) for r in rows]


async def _pending_for_doc(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    doc_type_code: str,
) -> int:
    q = await db.execute(
        select(func.count())
        .select_from(CandidatePipelineOverride)
        .where(
            and_(
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
                CandidatePipelineOverride.doc_type_code == doc_type_code,
                CandidatePipelineOverride.status == STATUS_PENDING,
            )
        )
    )
    return int(q.scalar_one() or 0)


async def _pending_for_requirement(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    requirement_code: str,
) -> int:
    q = await db.execute(
        select(func.count())
        .select_from(CandidatePipelineOverride)
        .where(
            and_(
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
                CandidatePipelineOverride.requirement_code == requirement_code,
                CandidatePipelineOverride.status == STATUS_PENDING,
            )
        )
    )
    return int(q.scalar_one() or 0)


async def create_override_request(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    actor_id: Optional[str],
    doc_type_code: Optional[str] = None,
    requirement_code: Optional[str] = None,
    reason: str,
    requested_scope: str,
) -> Dict[str, Any]:
    req_code = _norm_requirement_code(requirement_code)
    doc_code = normalize_doc_type(doc_type_code) if doc_type_code else ""
    if req_code and doc_code:
        raise ValueError("ambiguous_override_target")
    if not req_code and not doc_code:
        raise ValueError("missing_override_target")

    rs = str(requested_scope or "").strip().lower()
    if rs not in VALID_REQUESTED_SCOPES:
        raise ValueError("invalid_requested_scope")
    reason_clean = str(reason or "").strip()
    if len(reason_clean) < 8:
        raise ValueError("reason_too_short")
    if len(reason_clean) > 4000:
        raise ValueError("reason_too_long")

    if req_code:
        if req_code in NON_OVERRIDABLE_REQUIREMENT_CODES:
            raise ValueError("requirement_not_overridable")
        pending = await _pending_for_requirement(
            db, tenant_id=tenant_id, candidate_id=candidate_id, requirement_code=req_code
        )
        if pending > 0:
            raise ValueError("pending_exists")
        row = CandidatePipelineOverride(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            doc_type_code=None,
            requirement_code=req_code,
            status=STATUS_PENDING,
            requested_scope=rs,
            granted_scope=None,
            reason=reason_clean,
            review_note=None,
            requested_by_user_id=actor_id,
            reviewed_by_user_id=None,
            reviewed_at=None,
        )
    else:
        gates = await resolve_hiring_pipeline_gates(db, tenant_id, candidate_id=candidate_id)
        if doc_code in gates.effective_non_overridable_doc_types():
            raise ValueError("doc_type_not_overridable")
        pending = await _pending_for_doc(db, tenant_id=tenant_id, candidate_id=candidate_id, doc_type_code=doc_code)
        if pending > 0:
            raise ValueError("pending_exists")
        row = CandidatePipelineOverride(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            doc_type_code=doc_code,
            requirement_code=None,
            status=STATUS_PENDING,
            requested_scope=rs,
            granted_scope=None,
            reason=reason_clean,
            review_note=None,
            requested_by_user_id=actor_id,
            reviewed_by_user_id=None,
            reviewed_at=None,
        )

    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row_to_dict(row)


async def approve_override(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    override_id: str,
    actor_id: Optional[str],
    granted_scope: str,
    review_note: Optional[str] = None,
) -> Dict[str, Any]:
    gs = str(granted_scope or "").strip().lower()
    if gs not in VALID_GRANTED_SCOPES:
        raise ValueError("invalid_granted_scope")

    res = await db.execute(
        select(CandidatePipelineOverride).where(
            and_(
                CandidatePipelineOverride.id == override_id,
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
            )
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise ValueError("not_found")
    if row.status != STATUS_PENDING:
        raise ValueError("not_pending")

    req = str(row.requested_scope or SCOPE_PIPELINE).lower()
    if req == SCOPE_BOTH and gs == SCOPE_PIPELINE:
        # Manager may still approve pipeline-only if they choose (stricter than requested).
        pass

    row.status = STATUS_APPROVED
    row.granted_scope = gs
    row.reviewed_by_user_id = actor_id
    row.reviewed_at = _utcnow()
    if review_note is not None:
        note = str(review_note).strip()
        row.review_note = note[:4000] if note else None

    await db.flush()
    await db.refresh(row)
    return row_to_dict(row)


async def reject_override(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    override_id: str,
    actor_id: Optional[str],
    review_note: Optional[str] = None,
) -> Dict[str, Any]:
    res = await db.execute(
        select(CandidatePipelineOverride).where(
            and_(
                CandidatePipelineOverride.id == override_id,
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
            )
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise ValueError("not_found")
    if row.status != STATUS_PENDING:
        raise ValueError("not_pending")

    row.status = STATUS_REJECTED
    row.granted_scope = None
    row.reviewed_by_user_id = actor_id
    row.reviewed_at = _utcnow()
    if review_note is not None:
        note = str(review_note).strip()
        row.review_note = note[:4000] if note else None

    await db.flush()
    await db.refresh(row)
    return row_to_dict(row)


async def revoke_override(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    override_id: str,
    actor_id: Optional[str],
    review_note: Optional[str] = None,
) -> Dict[str, Any]:
    res = await db.execute(
        select(CandidatePipelineOverride).where(
            and_(
                CandidatePipelineOverride.id == override_id,
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
            )
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise ValueError("not_found")
    if row.status != STATUS_APPROVED:
        raise ValueError("not_approved")

    row.status = STATUS_REVOKED
    row.reviewed_by_user_id = actor_id
    row.reviewed_at = _utcnow()
    if review_note is not None:
        note = str(review_note).strip()
        row.review_note = note[:4000] if note else None

    await db.flush()
    await db.refresh(row)
    return row_to_dict(row)


async def approved_pipeline_relaxed_types(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> set[str]:
    """Doc types waived for pipeline UI / forward movement (pipeline or both)."""
    res = await db.execute(
        select(CandidatePipelineOverride.doc_type_code).where(
            and_(
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
                CandidatePipelineOverride.status == STATUS_APPROVED,
                CandidatePipelineOverride.granted_scope.in_((SCOPE_PIPELINE, SCOPE_BOTH)),
            )
        )
    )
    return {str(x) for x in res.scalars().all() if x}


async def approved_pipeline_relaxed_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> set[str]:
    """Requirement codes waived for pipeline UI / forward movement (pipeline or both)."""
    res = await db.execute(
        select(CandidatePipelineOverride.requirement_code).where(
            and_(
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
                CandidatePipelineOverride.status == STATUS_APPROVED,
                CandidatePipelineOverride.granted_scope.in_((SCOPE_PIPELINE, SCOPE_BOTH)),
                CandidatePipelineOverride.requirement_code.is_not(None),
            )
        )
    )
    return {_norm_requirement_code(x) for x in res.scalars().all() if x}


async def approved_handoff_relaxed_types(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> set[str]:
    res = await db.execute(
        select(CandidatePipelineOverride.doc_type_code).where(
            and_(
                CandidatePipelineOverride.tenant_id == tenant_id,
                CandidatePipelineOverride.candidate_id == candidate_id,
                CandidatePipelineOverride.status == STATUS_APPROVED,
                CandidatePipelineOverride.granted_scope == SCOPE_BOTH,
            )
        )
    )
    return {str(x) for x in res.scalars().all() if x}
