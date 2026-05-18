"""HR review document verification cards (PR3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_document_verification import (
    VERIFICATION_NEEDS_CORRECTION,
    VERIFICATION_NOT_REQUIRED,
    VERIFICATION_OPENED,
    VERIFICATION_PENDING,
    VERIFICATION_REJECTED,
    VERIFICATION_TERMINAL_OK,
    VERIFICATION_VERIFIED,
    WorkforceHrDocumentVerification,
)
from backend.app.models.workforce_hr_document_context import WorkforceHrDocumentContext
from backend.app.models.workforce_hr_review import WorkforceHrReview, HR_REVIEW_TERMINAL_STATUSES
from backend.app.services.audit import log_activity
from backend.app.services.hr_verified_field_catalog import FIELD_SPECS

# document_key -> checklist item that this card primarily supports
DOC_KEY_CHECKLIST: dict[str, str] = {
    "Legal stay": "legal_stay_verified",
    "Work permit": "work_permit_verified",
    "Red paper": "red_paper_verified",
    "Medical": "documents_uploaded",
    "Psychological": "documents_uploaded",
}

VERIFICATION_GATED_CHECKLIST = frozenset(
    {
        "documents_uploaded",
        "legal_stay_verified",
        "work_permit_verified",
        "red_paper_verified",
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dig(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _build_profile_context(
    employee: Optional[WorkforceEmployee],
    document: Optional[Document],
    context_row: Optional[WorkforceHrDocumentContext],
    eligibility: Optional[dict[str, Any]],
) -> dict[str, Any]:
    snap = employee.candidate_snapshot if employee and isinstance(employee.candidate_snapshot, dict) else {}
    meta = employee.meta if employee and isinstance(employee.meta, dict) else {}
    doc_meta = document.meta if document and isinstance(document.meta, dict) else {}
    return {
        "employee": {
            "display_name": employee.display_name if employee else None,
            "hire_date": str(employee.hire_date) if employee and employee.hire_date else None,
            "meta": meta,
        },
        "snapshot": snap,
        "document": {
            "doc_type": document.doc_type if document else None,
            "expires_at": (
                document.expires_at.isoformat()
                if document and getattr(document, "expires_at", None)
                else None
            ),
            "meta": doc_meta,
        },
        "context": {
            "context_type": context_row.context_type if context_row else None,
            "expires_at": context_row.expires_at.isoformat() if context_row and context_row.expires_at else None,
        },
        "eligibility": eligibility or {},
    }


def build_fields_to_review(
    document_key: str,
    profile_ctx: dict[str, Any],
    reviewed_fields: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    specs = FIELD_SPECS.get(document_key, FIELD_SPECS.get("Medical", []))
    reviewed = reviewed_fields if isinstance(reviewed_fields, dict) else {}
    out: list[dict[str, Any]] = []
    for spec in specs:
        code = str(spec["field_code"])
        values: dict[str, Any] = {}
        for pk in spec.get("profile_keys") or []:
            v = _dig(profile_ctx, pk)
            if v is not None and str(v).strip() != "":
                values[pk] = v
        needs_manual = len(values) == 0
        row_reviewed = reviewed.get(code) if isinstance(reviewed.get(code), dict) else {}
        out.append(
            {
                "field_code": code,
                "label": spec.get("label") or code,
                "downstream_use": list(spec.get("downstream_use") or []),
                "current_profile_values": values,
                "needs_manual_confirmation": needs_manual,
                "reviewed_value": row_reviewed.get("value"),
                "review_comment": row_reviewed.get("comment"),
                "confirmed": bool(row_reviewed.get("confirmed")),
            }
        )
    return out


async def _load_context_row(
    db: AsyncSession,
    tenant_id: str,
    employee_id: Optional[str],
    document_id: Optional[str],
) -> Optional[WorkforceHrDocumentContext]:
    if not employee_id or not document_id:
        return None
    return (
        await db.execute(
            select(WorkforceHrDocumentContext).where(
                WorkforceHrDocumentContext.tenant_id == tenant_id,
                WorkforceHrDocumentContext.employee_id == employee_id,
                WorkforceHrDocumentContext.document_id == document_id,
            )
        )
    ).scalar_one_or_none()


async def list_verifications_for_review(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
) -> list[WorkforceHrDocumentVerification]:
    tid = str(tenant_id).strip()
    rid = str(review.id).strip()
    rows = (
        await db.execute(
            select(WorkforceHrDocumentVerification)
            .where(
                WorkforceHrDocumentVerification.tenant_id == tid,
                WorkforceHrDocumentVerification.hr_review_id == rid,
            )
            .order_by(WorkforceHrDocumentVerification.document_key)
        )
    ).scalars().all()
    return list(rows)


async def ensure_verification_rows(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    approval_rows: list[dict[str, Any]],
) -> dict[str, WorkforceHrDocumentVerification]:
    tid = str(tenant_id).strip()
    existing = {v.document_key: v for v in await list_verifications_for_review(db, tid, review)}
    by_key: dict[str, WorkforceHrDocumentVerification] = {}
    for row in approval_rows:
        key = str(row.get("document_key") or row.get("label") or "").strip()
        if not key:
            continue
        v = existing.get(key)
        if v is None:
            v = WorkforceHrDocumentVerification(
                tenant_id=tid,
                hr_review_id=review.id,
                employee_id=review.employee_id,
                handoff_id=review.handoff_id,
                document_key=key,
                document_id=row.get("document_id"),
                document_type=row.get("context_type"),
                checklist_item_code=DOC_KEY_CHECKLIST.get(key, "documents_uploaded"),
                required=True,
                verification_status=VERIFICATION_PENDING,
            )
            db.add(v)
            existing[key] = v
        else:
            v.document_id = row.get("document_id") or v.document_id
            v.document_type = row.get("context_type") or v.document_type
            v.employee_id = review.employee_id or v.employee_id
            v.handoff_id = review.handoff_id or v.handoff_id
        if str(row.get("status") or "").lower() == "missing" and not row.get("document_id"):
            if v.verification_status not in VERIFICATION_TERMINAL_OK:
                v.verification_status = VERIFICATION_PENDING
        by_key[key] = v
    await db.flush()
    return by_key


def verification_blocks_approval(verifications: list[WorkforceHrDocumentVerification], approval_rows: list[dict]) -> bool:
    by_key = {v.document_key: v for v in verifications}
    for row in approval_rows:
        key = str(row.get("document_key") or "").strip()
        if not key:
            continue
        if str(row.get("status") or "").lower() == "missing":
            return True
        v = by_key.get(key)
        if not v or v.verification_status not in VERIFICATION_TERMINAL_OK:
            return True
    return False


async def sync_checklist_from_verifications(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    approval_rows: list[dict[str, Any]],
) -> None:
    """Auto-satisfy verification-gated checklist items from document card states."""
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        return
    verifications = await list_verifications_for_review(db, tenant_id, review)
    by_key = {v.document_key: v for v in verifications}
    all_docs_ok = not verification_blocks_approval(verifications, approval_rows)

    cl = dict(review.checklist_json or {"items": []})
    items = list(cl.get("items") or [])
    changed = False

    def set_item(code: str, *, satisfied: bool, blockers: list[str]) -> None:
        nonlocal changed
        for i, it in enumerate(items):
            if not isinstance(it, dict) or str(it.get("item_code") or "") != code:
                continue
            new_status = "satisfied" if satisfied else "blocked"
            if str(it.get("status")) == new_status and it.get("source") == "verification":
                return
            items[i] = {
                **it,
                "status": new_status,
                "source": "verification",
                "blockers": blockers,
                "basis": {**(it.get("basis") or {}), "verification_sync": True},
            }
            changed = True
            return

    for key, code in DOC_KEY_CHECKLIST.items():
        v = by_key.get(key)
        if v is None:
            continue
        ok = v.verification_status in VERIFICATION_TERMINAL_OK
        blockers = [] if ok else [f"document_verification:{key}"]
        set_item(code, satisfied=ok, blockers=blockers)

    set_item(
        "documents_uploaded",
        satisfied=all_docs_ok,
        blockers=[] if all_docs_ok else ["document_verification_incomplete"],
    )

    if changed:
        cl["items"] = items
        review.checklist_json = cl
        from backend.app.services.workforce_hr_review import _recompute_review_blockers_from_checklist

        _recompute_review_blockers_from_checklist(review)
        await db.flush()


async def enrich_approval_rows_with_verification(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    approval_rows: list[dict[str, Any]],
    *,
    employee: Optional[WorkforceEmployee] = None,
    eligibility: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    by_key = await ensure_verification_rows(db, tenant_id, review, approval_rows)
    out: list[dict[str, Any]] = []
    for row in approval_rows:
        key = str(row.get("document_key") or "").strip()
        v = by_key.get(key)
        r = dict(row)
        if not v:
            out.append(r)
            continue
        doc: Optional[Document] = None
        if v.document_id:
            doc = await db.get(Document, str(v.document_id))
        ctx_row = await _load_context_row(db, tenant_id, review.employee_id, v.document_id)
        profile_ctx = _build_profile_context(employee, doc, ctx_row, eligibility)
        fields = build_fields_to_review(key, profile_ctx, v.reviewed_fields_json)
        r.update(
            {
                "document_type": v.document_type or r.get("context_type"),
                "required": bool(v.required),
                "verification_status": v.verification_status,
                "linked_checklist_item": v.checklist_item_code,
                "fields_to_review": fields,
                "reviewed_fields": v.reviewed_fields_json or {},
                "rejection_reason": v.rejection_reason,
                "correction_note": v.correction_note,
                "verified": v.verification_status == VERIFICATION_VERIFIED,
                "verification_id": v.id,
                "actions": {
                    "can_open": bool(r.get("open_url") or r.get("document_id")),
                    "can_verify": v.verification_status in (VERIFICATION_OPENED, VERIFICATION_PENDING, VERIFICATION_NEEDS_CORRECTION)
                    and bool(r.get("document_id")),
                    "can_reject": bool(r.get("document_id")),
                    "can_request_correction": bool(r.get("document_id")),
                },
            }
        )
        if v.verification_status == VERIFICATION_VERIFIED:
            r["status"] = "verified"
        elif v.verification_status == VERIFICATION_REJECTED:
            r["status"] = "rejected"
        elif v.verification_status == VERIFICATION_NEEDS_CORRECTION:
            r["status"] = "needs_correction"
        elif v.verification_status == VERIFICATION_OPENED:
            r["status"] = "opened"
        out.append(r)
    return out


async def _get_verification_row(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    document_key: str,
) -> WorkforceHrDocumentVerification:
    key = str(document_key).strip()
    row = (
        await db.execute(
            select(WorkforceHrDocumentVerification).where(
                WorkforceHrDocumentVerification.tenant_id == tenant_id,
                WorkforceHrDocumentVerification.hr_review_id == review.id,
                WorkforceHrDocumentVerification.document_key == key,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise ValueError("VERIFICATION_NOT_FOUND")
    return row


async def _audit_verification(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_user_id: str,
    review: WorkforceHrReview,
    document_key: str,
    action: str,
    payload: dict[str, Any],
) -> None:
    await log_activity(
        db,
        tenant_id=tenant_id,
        action=f"workforce.hr_review.document_verification.{action}",
        actor_id=actor_user_id,
        target_type="workforce_hr_review",
        target_id=str(review.id),
        payload={"document_key": document_key, **payload},
    )


async def mark_document_opened(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    document_key: str,
    actor_user_id: str,
) -> WorkforceHrDocumentVerification:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    row = await _get_verification_row(db, tenant_id, review, document_key)
    if row.verification_status == VERIFICATION_PENDING:
        row.verification_status = VERIFICATION_OPENED
    row.opened_by_user_id = actor_user_id
    row.opened_at = _now()
    await db.flush()
    await _audit_verification(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        review=review,
        document_key=document_key,
        action="opened",
        payload={"verification_status": row.verification_status},
    )
    return row


async def save_document_reviewed_fields(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    document_key: str,
    actor_user_id: str,
    reviewed_fields: dict[str, Any],
) -> WorkforceHrDocumentVerification:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    row = await _get_verification_row(db, tenant_id, review, document_key)
    row.reviewed_fields_json = reviewed_fields
    if row.verification_status == VERIFICATION_PENDING:
        row.verification_status = VERIFICATION_OPENED
    row.opened_by_user_id = row.opened_by_user_id or actor_user_id
    row.opened_at = row.opened_at or _now()
    await db.flush()
    await _audit_verification(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        review=review,
        document_key=document_key,
        action="reviewed",
        payload={"fields": list(reviewed_fields.keys())},
    )
    return row


async def verify_document(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    document_key: str,
    actor_user_id: str,
    reviewed_fields: Optional[dict[str, Any]] = None,
) -> WorkforceHrDocumentVerification:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    row = await _get_verification_row(db, tenant_id, review, document_key)
    if not row.document_id:
        raise ValueError("DOCUMENT_MISSING")
    if reviewed_fields is not None:
        row.reviewed_fields_json = reviewed_fields
    row.verification_status = VERIFICATION_VERIFIED
    row.verified_by_user_id = actor_user_id
    row.verified_at = _now()
    row.rejection_reason = None
    row.correction_note = None
    if review.employee_id and row.document_id:
        ctx = await _load_context_row(db, tenant_id, review.employee_id, row.document_id)
        if ctx:
            ctx.verified = True
            ctx.verification_status = VERIFICATION_VERIFIED
    await db.flush()
    await _audit_verification(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        review=review,
        document_key=document_key,
        action="verify",
        payload={"document_id": row.document_id},
    )
    from backend.app.services import hr_verified_fields as vf_svc

    await vf_svc.sync_from_document_verification(
        db,
        tenant_id=tenant_id,
        review=review,
        doc_verification=row,
        actor_user_id=actor_user_id,
    )
    return row


async def reject_document(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    document_key: str,
    actor_user_id: str,
    reason: str,
) -> WorkforceHrDocumentVerification:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    row = await _get_verification_row(db, tenant_id, review, document_key)
    row.verification_status = VERIFICATION_REJECTED
    row.rejection_reason = reason.strip()
    row.verified_by_user_id = None
    row.verified_at = None
    if review.employee_id and row.document_id:
        ctx = await _load_context_row(db, tenant_id, review.employee_id, row.document_id)
        if ctx:
            ctx.verified = False
            ctx.verification_status = VERIFICATION_REJECTED
    await db.flush()
    await _audit_verification(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        review=review,
        document_key=document_key,
        action="reject",
        payload={"reason": reason[:200]},
    )
    return row


async def request_document_correction(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    document_key: str,
    actor_user_id: str,
    note: str,
) -> WorkforceHrDocumentVerification:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    row = await _get_verification_row(db, tenant_id, review, document_key)
    row.verification_status = VERIFICATION_NEEDS_CORRECTION
    row.correction_note = note.strip()
    row.verified_by_user_id = None
    row.verified_at = None
    if review.employee_id and row.document_id:
        ctx = await _load_context_row(db, tenant_id, review.employee_id, row.document_id)
        if ctx:
            ctx.verified = False
            ctx.verification_status = VERIFICATION_NEEDS_CORRECTION
    await db.flush()
    await _audit_verification(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        review=review,
        document_key=document_key,
        action="request_correction",
        payload={"note": note[:200]},
    )
    return row
