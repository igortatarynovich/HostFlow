"""HR Inbox queue: internal-HR handoffs + snapshot + workforce linkage."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_review import (
    HR_REVIEW_STATUS_APPROVED,
    HR_REVIEW_STATUS_REJECTED,
    HR_REVIEW_STATUS_RETURNED,
    HR_REVIEW_STATUS_WAITING_DOCUMENTS,
    HR_REVIEW_STATUS_WAITING_PAYMENTS,
    HR_REVIEW_STATUS_WAITING_RED_PAPER,
    HR_REVIEW_STATUS_WAITING_WORK_PERMIT,
    WorkforceHrReview,
)
from backend.app.models.workforce_hr_document_verification import (
    VERIFICATION_TERMINAL_OK,
    WorkforceHrDocumentVerification,
)
from backend.app.services.tenant_hr_flags import delayed_hr_workforce_creation_enabled
from backend.app.services.workforce_hr_review import ensure_hr_review_for_handoff

# Operational queue codes for HR inbox (Stage B UX).
QUEUE_AWAITING_PICKUP = "awaiting_hr_pickup"
QUEUE_HR_REVIEW_IN_PROGRESS = "hr_review_in_progress"
QUEUE_AWAITING_DOCUMENTS = "awaiting_documents"
QUEUE_AWAITING_PAYMENTS = "awaiting_payments"
QUEUE_AWAITING_WORK_PERMIT = "awaiting_work_permit"
QUEUE_AWAITING_RED_PAPER = "awaiting_red_paper"
QUEUE_APPROVED = "approved_for_employment"
QUEUE_RETURNED = "returned_to_recruitment"
QUEUE_REJECTED = "rejected_by_hr"


def _candidate_display_from_snapshot(snapshot: dict[str, Any] | None) -> str | None:
    if not isinstance(snapshot, dict):
        return None
    cand = snapshot.get("candidate")
    if isinstance(cand, dict):
        parts = [str(cand.get("first_name") or "").strip(), str(cand.get("last_name") or "").strip()]
        name = " ".join(p for p in parts if p).strip()
        if name:
            return name
        email = str(cand.get("email") or "").strip()
        if email:
            return email
    summary = snapshot.get("candidate_snapshot_summary")
    if isinstance(summary, dict):
        dn = str(summary.get("display_name") or summary.get("name") or "").strip()
        if dn:
            return dn
    return None


def _transfer_summary_from_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict):
        return None
    cand = snapshot.get("candidate")
    base: dict[str, Any] = cand if isinstance(cand, dict) else {}
    if not base:
        summary = snapshot.get("candidate_snapshot_summary")
        base = summary if isinstance(summary, dict) else snapshot
    vacancy = snapshot.get("vacancy") if isinstance(snapshot.get("vacancy"), dict) else {}
    out = {
        "first_name": base.get("first_name"),
        "last_name": base.get("last_name"),
        "email": base.get("email"),
        "phone": base.get("phone"),
        "citizenship": base.get("citizenship") or snapshot.get("citizenship"),
        "work_country": base.get("work_country") or snapshot.get("work_country"),
        "position_category": base.get("position_category") or snapshot.get("position_category"),
        "vacancy_title": vacancy.get("title") or base.get("vacancy_title"),
        "documents_count": snapshot.get("documents_count") or base.get("documents_count"),
    }
    cleaned = {k: v for k, v in out.items() if v not in (None, "")}
    return cleaned or None


async def _document_verification_counts_by_review(
    db: AsyncSession,
    *,
    tenant_id: str,
    review_ids: list[str],
) -> dict[str, tuple[int, int]]:
    if not review_ids:
        return {}
    rows = (
        await db.execute(
            select(
                WorkforceHrDocumentVerification.hr_review_id,
                WorkforceHrDocumentVerification.verification_status,
            ).where(
                WorkforceHrDocumentVerification.tenant_id == str(tenant_id),
                WorkforceHrDocumentVerification.hr_review_id.in_(review_ids),
                WorkforceHrDocumentVerification.required.is_(True),
            )
        )
    ).all()
    totals: dict[str, int] = defaultdict(int)
    verified: dict[str, int] = defaultdict(int)
    for rid, status in rows:
        key = str(rid)
        totals[key] += 1
        if str(status or "") in VERIFICATION_TERMINAL_OK:
            verified[key] += 1
    return {k: (verified.get(k, 0), totals[k]) for k in totals}


def derive_operational_queue(
    *,
    handoff_status: str,
    hr_review_status: str | None,
    workforce_employee_id: str | None,
    employment_approved: bool,
) -> str:
    """Map handoff + review to HR inbox queue semantics."""
    hs = str(handoff_status or "").strip()
    rs = str(hr_review_status or "").strip() if hr_review_status else None

    if hs == "pending_review":
        return QUEUE_AWAITING_PICKUP
    if hs == "returned" or rs == HR_REVIEW_STATUS_RETURNED:
        return QUEUE_RETURNED
    if hs == "rejected" or rs == HR_REVIEW_STATUS_REJECTED:
        return QUEUE_REJECTED
    if employment_approved or rs == HR_REVIEW_STATUS_APPROVED:
        return QUEUE_APPROVED
    if rs == HR_REVIEW_STATUS_WAITING_DOCUMENTS:
        return QUEUE_AWAITING_DOCUMENTS
    if rs == HR_REVIEW_STATUS_WAITING_PAYMENTS:
        return QUEUE_AWAITING_PAYMENTS
    if rs == HR_REVIEW_STATUS_WAITING_WORK_PERMIT:
        return QUEUE_AWAITING_WORK_PERMIT
    if rs == HR_REVIEW_STATUS_WAITING_RED_PAPER:
        return QUEUE_AWAITING_RED_PAPER
    if hs == "accepted":
        return QUEUE_HR_REVIEW_IN_PROGRESS
    return QUEUE_HR_REVIEW_IN_PROGRESS


async def _reviews_by_handoff_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_ids: list[str],
) -> dict[str, WorkforceHrReview]:
    if not handoff_ids:
        return {}
    rows = (
        await db.execute(
            select(WorkforceHrReview).where(
                WorkforceHrReview.tenant_id == str(tenant_id),
                WorkforceHrReview.handoff_id.in_(handoff_ids),
            )
        )
    ).scalars().all()
    return {str(r.handoff_id): r for r in rows if r.handoff_id}


async def _ensure_reviews_for_inbox_rows(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str,
    handoffs: Sequence[CandidateHandoff],
    reviews_by_hid: dict[str, WorkforceHrReview],
    delayed_workforce: bool,
) -> dict[str, WorkforceHrReview]:
    """Materialize review rows for accepted internal-HR handoffs (Stage B compatibility)."""
    if str(status) != "accepted" or not delayed_workforce:
        return reviews_by_hid
    out = dict(reviews_by_hid)
    for handoff in handoffs:
        hid = str(handoff.id)
        if hid in out or not handoff.candidate_id:
            continue
        out[hid] = await ensure_hr_review_for_handoff(
            db,
            tenant_id=tenant_id,
            handoff_id=hid,
            candidate_id=str(handoff.candidate_id),
        )
    return out


def enrich_handoff_inbox_row(
    *,
    handoff: CandidateHandoff,
    snapshot: dict[str, Any] | None,
    workforce_employee_id: str | None,
    review: WorkforceHrReview | None,
    delayed_workforce: bool,
    documents_verified_count: int | None = None,
    documents_total_count: int | None = None,
) -> dict[str, Any]:
    review_status = review.status if review else None
    emp_id = workforce_employee_id or (str(review.employee_id) if review and review.employee_id else None)
    employment_approved = review_status == HR_REVIEW_STATUS_APPROVED
    operational_queue = derive_operational_queue(
        handoff_status=str(handoff.status),
        hr_review_status=review_status,
        workforce_employee_id=emp_id,
        employment_approved=employment_approved,
    )
    return {
        "handoff": handoff,
        "snapshot": snapshot,
        "workforce_employee_id": emp_id,
        "hr_review_id": str(review.id) if review else None,
        "hr_review_status": review_status,
        "operational_queue": operational_queue,
        "candidate_display_name": _candidate_display_from_snapshot(snapshot),
        "delayed_hr_workforce_creation": delayed_workforce,
        "can_approve_for_employment": bool(
            review
            and review_status not in (HR_REVIEW_STATUS_APPROVED, HR_REVIEW_STATUS_RETURNED, HR_REVIEW_STATUS_REJECTED)
            and operational_queue
            not in (QUEUE_AWAITING_PICKUP, QUEUE_APPROVED, QUEUE_RETURNED, QUEUE_REJECTED)
        ),
        "awaiting_employment_approval": bool(
            delayed_workforce
            and str(handoff.status) == "accepted"
            and not employment_approved
            and operational_queue not in (QUEUE_RETURNED, QUEUE_REJECTED)
        ),
        "transfer_summary": _transfer_summary_from_snapshot(snapshot),
        "documents_verified_count": documents_verified_count,
        "documents_total_count": documents_total_count,
    }


async def _workforce_employee_id_by_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoffs: Sequence[CandidateHandoff],
) -> dict[str, str]:
    """Map handoff id -> workforce_employee.id using meta.internal_hr_handoff_id."""
    if not handoffs:
        return {}
    cand_ids = {str(h.candidate_id) for h in handoffs if h.candidate_id}
    if not cand_ids:
        return {}
    rows = await db.execute(
        select(WorkforceEmployee).where(
            WorkforceEmployee.tenant_id == str(tenant_id),
            WorkforceEmployee.candidate_id.in_(list(cand_ids)),
        )
    )
    out: dict[str, str] = {}
    for emp in rows.scalars().all():
        hid = (emp.meta or {}).get("internal_hr_handoff_id")
        if hid:
            out[str(hid)] = str(emp.id)
    return out


async def list_internal_hr_handoffs_for_hr_inbox(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Return paginated inbox rows for internal HR lane (`destination == internal_hr`)."""
    tid = str(tenant_id).strip()
    st = str(status).strip()
    if st not in ("pending_review", "accepted"):
        raise ValueError("status must be pending_review or accepted")

    base = (
        select(CandidateHandoff, CandidateHandoffSnapshot)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .outerjoin(
            CandidateHandoffSnapshot,
            CandidateHandoffSnapshot.handoff_id == CandidateHandoff.id,
        )
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status == st,
            Candidate.deleted_at.is_(None),
        )
    )

    count_stmt = (
        select(func.count())
        .select_from(CandidateHandoff)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status == st,
            Candidate.deleted_at.is_(None),
        )
    )
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    stmt = (
        base.order_by(CandidateHandoff.requested_at.desc())
        .offset(max(0, offset))
        .limit(min(max(1, limit), 200))
    )
    result = await db.execute(stmt)
    pairs = result.all()

    handoffs_only = [p[0] for p in pairs]
    wf_by_hid = await _workforce_employee_id_by_handoff(db, tenant_id=tid, handoffs=handoffs_only)
    hid_list = [str(h.id) for h in handoffs_only]
    delayed_workforce = await delayed_hr_workforce_creation_enabled(db, tid)
    reviews_by_hid = await _reviews_by_handoff_ids(db, tenant_id=tid, handoff_ids=hid_list)
    reviews_by_hid = await _ensure_reviews_for_inbox_rows(
        db,
        tenant_id=tid,
        status=st,
        handoffs=handoffs_only,
        reviews_by_hid=reviews_by_hid,
        delayed_workforce=delayed_workforce,
    )

    review_ids = [str(r.id) for r in reviews_by_hid.values() if r and r.id]
    doc_counts = await _document_verification_counts_by_review(db, tenant_id=tid, review_ids=review_ids)

    items: list[dict[str, Any]] = []
    for handoff, snap in pairs:
        snap_dict = dict(snap.payload) if snap is not None else None
        hid = str(handoff.id)
        review = reviews_by_hid.get(hid)
        verified_n, total_n = (None, None)
        if review and review.id:
            counts = doc_counts.get(str(review.id))
            if counts:
                verified_n, total_n = counts
        items.append(
            enrich_handoff_inbox_row(
                handoff=handoff,
                snapshot=snap_dict,
                workforce_employee_id=wf_by_hid.get(hid),
                review=review,
                delayed_workforce=delayed_workforce,
                documents_verified_count=verified_n,
                documents_total_count=total_n,
            )
        )
    return items, total


async def get_internal_hr_handoff_inbox_row(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
) -> dict[str, Any] | None:
    """Single enriched inbox row for handoff detail screen."""
    tid = str(tenant_id).strip()
    hid = str(handoff_id).strip()
    handoff = await db.get(CandidateHandoff, hid)
    if not handoff or str(handoff.agency_tenant_id) != tid:
        return None
    if str(getattr(handoff, "destination", "") or "").strip().lower() != "internal_hr":
        return None
    snap_row = (
        await db.execute(
            select(CandidateHandoffSnapshot).where(CandidateHandoffSnapshot.handoff_id == hid)
        )
    ).scalar_one_or_none()
    snap_dict = dict(snap_row.payload) if snap_row is not None else None
    wf_map = await _workforce_employee_id_by_handoff(db, tenant_id=tid, handoffs=[handoff])
    delayed_workforce = await delayed_hr_workforce_creation_enabled(db, tid)
    reviews = await _reviews_by_handoff_ids(db, tenant_id=tid, handoff_ids=[hid])
    reviews = await _ensure_reviews_for_inbox_rows(
        db,
        tenant_id=tid,
        status=str(handoff.status or ""),
        handoffs=[handoff],
        reviews_by_hid=reviews,
        delayed_workforce=delayed_workforce,
    )
    review = reviews.get(hid)
    verified_n, total_n = (None, None)
    if review and review.id:
        doc_counts = await _document_verification_counts_by_review(
            db, tenant_id=tid, review_ids=[str(review.id)]
        )
        counts = doc_counts.get(str(review.id))
        if counts:
            verified_n, total_n = counts
    return enrich_handoff_inbox_row(
        handoff=handoff,
        snapshot=snap_dict,
        workforce_employee_id=wf_map.get(hid),
        review=review,
        delayed_workforce=delayed_workforce,
        documents_verified_count=verified_n,
        documents_total_count=total_n,
    )
