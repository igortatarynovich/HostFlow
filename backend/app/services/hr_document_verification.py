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
from backend.app.services.hr_handoff_profile_context import load_handoff_profile_namespace
from backend.app.services.hr_verified_field_catalog import (
    DATA_ONLY_VERIFICATION_KEYS,
    FIELD_SPECS,
    OPTIONAL_FILE_VERIFICATION_KEYS,
    resolve_field_input_type,
)
from backend.app.services.hr_profile_address import promote_address_fields

# document_key -> checklist item that this card primarily supports
# Transport document cards are optional when position is not driver (PR12 sequential flow).
OPTIONAL_FOR_NON_DRIVER_DOC_KEYS: frozenset[str] = frozenset(
    {"Driver license", "Code95", "Tacho card"},
)


def document_required_for_position(document_key: str, position_category: Optional[str]) -> bool:
    if str(document_key or "").strip() in OPTIONAL_FOR_NON_DRIVER_DOC_KEYS:
        from backend.app.services.hr_verification_requirements import is_driver_position

        return is_driver_position(position_category)
    return True


DOC_KEY_CHECKLIST: dict[str, str] = {
    "Legal stay": "legal_stay_verified",
    "Work permit": "work_permit_verified",
    "Red paper": "red_paper_verified",
    "Medical": "documents_uploaded",
    "Psychological": "documents_uploaded",
    "Driver license": "documents_uploaded",
    "Code95": "documents_uploaded",
    "Tacho card": "documents_uploaded",
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


def _format_profile_value(value: Any) -> Any:
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                chunks = [
                    str(item.get(k) or "").strip()
                    for k in ("position", "employer_name", "company", "country", "date_from", "date_to")
                    if str(item.get(k) or "").strip()
                ]
                line = " · ".join(chunks)
                if line:
                    parts.append(line)
            elif item is not None and str(item).strip():
                parts.append(str(item).strip())
        return "\n".join(parts) if parts else None
    if isinstance(value, dict):
        return str(value.get("line1") or value.get("address") or value).strip() or None
    return value


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
    *,
    handoff: Optional[dict[str, Any]] = None,
    candidate_live: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    snap = dict(employee.candidate_snapshot) if employee and isinstance(employee.candidate_snapshot, dict) else {}
    if candidate_live:
        for k, v in candidate_live.items():
            if v is not None and str(v).strip() and k not in snap:
                snap[k] = v
    meta = employee.meta if employee and isinstance(employee.meta, dict) else {}
    personal_meta = meta.get("personal_data") if isinstance(meta.get("personal_data"), dict) else {}
    contacts = meta.get("contacts") if isinstance(meta.get("contacts"), dict) else {}
    if not contacts and isinstance(snap.get("contacts"), dict):
        contacts = snap.get("contacts")
    exp_raw = snap.get("experience") or snap.get("employments")
    if not exp_raw and isinstance(snap.get("profile"), dict):
        exp_raw = snap["profile"].get("experience")
    experience_summary = _format_profile_value(exp_raw)
    doc_meta = document.meta if document and isinstance(document.meta, dict) else {}
    issue = None
    if document:
        issue = getattr(document, "issue_date", None)
    exp = None
    if document:
        exp = getattr(document, "expire_date", None) or getattr(document, "expires_at", None)
    doc_number = None
    if document:
        doc_number = getattr(document, "number", None) or doc_meta.get("document_number") or doc_meta.get("passport_number")
    ctx: dict[str, Any] = {
        "employee": {
            "display_name": employee.display_name if employee else None,
            "hire_date": str(employee.hire_date) if employee and employee.hire_date else None,
            "meta": meta,
        },
        "snapshot": {
            **snap,
            "birth_date": snap.get("birth_date") or personal_meta.get("birth_date"),
            "passport_number": snap.get("passport_number") or personal_meta.get("passport_number"),
            "passport_series": snap.get("passport_series") or personal_meta.get("passport_series"),
            "passport_issue_date": snap.get("passport_issue_date") or personal_meta.get("passport_issue_date"),
            "experience_summary": experience_summary or snap.get("experience_summary"),
            "phone": snap.get("phone") or contacts.get("phone") or personal_meta.get("phone"),
            "email": snap.get("email") or contacts.get("email") or personal_meta.get("email"),
            "address": snap.get("address") or personal_meta.get("address") or contacts.get("address"),
            "city": snap.get("city") or personal_meta.get("city"),
            "postal_code": snap.get("postal_code") or personal_meta.get("postal_code"),
        },
        "contacts": contacts,
        "document": {
            "doc_type": document.doc_type if document else None,
            "number": str(doc_number).strip() if doc_number else None,
            "issue_date": issue.isoformat() if issue and hasattr(issue, "isoformat") else (str(issue) if issue else None),
            "expires_at": exp.isoformat() if exp and hasattr(exp, "isoformat") else (str(exp) if exp else None),
            "meta": doc_meta,
        },
        "context": {
            "context_type": context_row.context_type if context_row else None,
            "expires_at": context_row.expires_at.isoformat() if context_row and context_row.expires_at else None,
        },
        "eligibility": eligibility or {},
    }
    if handoff:
        ctx["handoff"] = handoff
    if candidate_live:
        ctx["candidate"] = {"extra": candidate_live, **{k: v for k, v in candidate_live.items() if k != "extra"}}

    snap_out = ctx["snapshot"] if isinstance(ctx.get("snapshot"), dict) else {}
    extra_snap = snap.get("extra") if isinstance(snap.get("extra"), dict) else {}
    personal_snap = snap.get("personal_data") if isinstance(snap.get("personal_data"), dict) else {}
    hr_identity = snap.get("hr_identity") if isinstance(snap.get("hr_identity"), dict) else {}
    handoff_cand = handoff.get("candidate") if isinstance(handoff, dict) and isinstance(handoff.get("candidate"), dict) else {}
    cand_extra = {}
    if isinstance(ctx.get("candidate"), dict):
        cand_extra = ctx["candidate"].get("extra") if isinstance(ctx["candidate"].get("extra"), dict) else {}
    promote_address_fields(
        snap_out,
        snap_out.get("address"),
        personal_meta.get("address"),
        personal_snap.get("address"),
        extra_snap.get("address"),
        hr_identity.get("address"),
        handoff_cand.get("address"),
        cand_extra.get("address"),
    )
    if isinstance(handoff_cand, dict):
        for key in ("address_country", "city", "postal_code", "address_street", "address_house", "address_apt"):
            if handoff_cand.get(key):
                snap_out.setdefault(key, handoff_cand.get(key))
    ctx["snapshot"] = snap_out
    return ctx


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
            v = _format_profile_value(_dig(profile_ctx, pk))
            if v is not None and str(v).strip() != "":
                values[pk] = v
        needs_manual = len(values) == 0
        row_reviewed = reviewed.get(code) if isinstance(reviewed.get(code), dict) else {}
        out.append(
            {
                "field_code": code,
                "label": spec.get("label") or code,
                "input_type": resolve_field_input_type(code, spec),
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
    from backend.app.services.hr_verification_requirements import resolve_position_category_for_review

    position_category = await resolve_position_category_for_review(
        db,
        tenant_id,
        employee_id=review.employee_id,
        candidate_id=review.candidate_id,
    )
    tid = str(tenant_id).strip()
    existing = {v.document_key: v for v in await list_verifications_for_review(db, tid, review)}
    by_key: dict[str, WorkforceHrDocumentVerification] = {}
    for row in approval_rows:
        key = str(row.get("document_key") or row.get("label") or "").strip()
        if not key:
            continue
        req = document_required_for_position(key, position_category)
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
                required=req,
                verification_status=VERIFICATION_NOT_REQUIRED if not req else VERIFICATION_PENDING,
            )
            db.add(v)
            existing[key] = v
        else:
            v.document_id = row.get("document_id") or v.document_id
            v.document_type = row.get("context_type") or v.document_type
            v.employee_id = review.employee_id or v.employee_id
            v.handoff_id = review.handoff_id or v.handoff_id
            v.required = req
            if not req and v.verification_status not in VERIFICATION_TERMINAL_OK:
                v.verification_status = VERIFICATION_NOT_REQUIRED
        if str(row.get("status") or "").lower() == "missing" and not row.get("document_id"):
            if not req:
                v.verification_status = VERIFICATION_NOT_REQUIRED
            elif v.verification_status not in VERIFICATION_TERMINAL_OK:
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
        v = by_key.get(key)
        if v is not None:
            required = v.required is not False
        elif row.get("required") is False:
            required = False
        else:
            required = True
        if not required:
            continue
        if str(row.get("status") or "").lower() == "missing":
            return True
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
    from backend.app.services.hr_handoff_profile_context import (
        _load_live_candidate_fields,
        load_recruiter_profile_namespace,
    )

    cid = str(
        (employee.candidate_id if employee and employee.candidate_id else None)
        or review.candidate_id
        or ""
    ).strip()
    handoff_ns = await load_recruiter_profile_namespace(
        db,
        tenant_id,
        handoff_id=review.handoff_id,
        candidate_id=cid or None,
    )
    _, _, candidate_flat = await _load_live_candidate_fields(db, cid or None)
    eligibility_full = dict(eligibility or {})
    if employee and review.employee_id:
        from backend.app.services.workforce_employees import get_work_eligibility_profile

        wel = await get_work_eligibility_profile(db, tenant_id, str(review.employee_id))
        if wel is not None:
            eligibility_full = {
                "citizenship": getattr(wel, "citizenship", None),
                "work_country": getattr(wel, "work_country", None),
                "pesel": getattr(wel, "pesel", None) or getattr(wel, "national_id", None),
                "position_category": getattr(wel, "position_category", None),
            }
    out: list[dict[str, Any]] = []
    for row in approval_rows:
        key = str(row.get("document_key") or "").strip()
        v = by_key.get(key)
        r = dict(row)
        if not v:
            out.append(r)
            continue
        doc: Optional[Document] = None
        doc_id = str(v.document_id or r.get("document_id") or "").strip()
        if doc_id:
            doc = await db.get(Document, str(doc_id))
            v.document_id = doc_id
        ctx_row = await _load_context_row(db, tenant_id, review.employee_id, doc_id or None)
        profile_ctx = _build_profile_context(
            employee,
            doc,
            ctx_row,
            eligibility_full,
            handoff=handoff_ns,
            candidate_live=candidate_flat,
        )
        fields = build_fields_to_review(key, profile_ctx, v.reviewed_fields_json)
        is_data_only = key in DATA_ONLY_VERIFICATION_KEYS
        is_optional_file = key in OPTIONAL_FILE_VERIFICATION_KEYS
        has_file = bool(r.get("open_url") or doc_id)
        can_verify_status = v.verification_status in (
            VERIFICATION_OPENED,
            VERIFICATION_PENDING,
            VERIFICATION_NEEDS_CORRECTION,
        )
        can_verify = can_verify_status and (
            bool(doc_id) or is_data_only or is_optional_file
        )
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
                "block_kind": "data_only"
                if is_data_only
                else ("optional_file" if is_optional_file else "document"),
                "file_required_for_confirm": not is_data_only and not is_optional_file,
                "actions": {
                    "can_open": bool(r.get("open_url") or doc_id),
                    "can_verify": can_verify,
                    "can_reject": bool(r.get("document_id")) and not is_data_only,
                    "can_request_correction": bool(r.get("document_id")) and not is_data_only,
                    "can_upload": is_optional_file or not is_data_only,
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


def _append_waiver_to_decision_basis(
    review: WorkforceHrReview,
    *,
    document_key: str,
    reason: str,
    actor_user_id: str,
) -> None:
    basis = dict(review.decision_basis_json) if isinstance(review.decision_basis_json, dict) else {}
    waivers = [w for w in (basis.get("requirement_waivers") or []) if isinstance(w, dict)]
    waivers.append(
        {
            "document_key": document_key,
            "reason": reason,
            "by_user_id": actor_user_id,
            "at": _now().isoformat(),
        }
    )
    basis["requirement_waivers"] = waivers[-50:]
    review.decision_basis_json = basis


async def waive_document_requirement(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    document_key: str,
    actor_user_id: str,
    reason: str,
) -> WorkforceHrDocumentVerification:
    """HR exception for recommended / vacancy-required docs (not hard legal blockers)."""
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    key = str(document_key or "").strip()
    note = str(reason or "").strip()
    if not note:
        raise ValueError("WAIVER_REASON_REQUIRED")

    from backend.app.services.hr_verification_plan import is_document_requirement_waivable
    from backend.app.services.hr_verification_requirements import resolve_position_category_for_review
    from backend.app.services.workforce_work_eligibility_journey import build_work_eligibility_journey

    journey: dict[str, Any] = {}
    if review.employee_id:
        journey = await build_work_eligibility_journey(db, tenant_id, str(review.employee_id))
    position_category = await resolve_position_category_for_review(
        db,
        tenant_id,
        employee_id=review.employee_id,
        candidate_id=review.candidate_id,
    )
    if not is_document_requirement_waivable(
        key, journey=journey, position_category=position_category
    ):
        raise ValueError("CANNOT_WAIVE_HARD_BLOCKER")

    row = await _get_verification_row(db, tenant_id, review, key)
    reviewed = dict(row.reviewed_fields_json) if isinstance(row.reviewed_fields_json, dict) else {}
    reviewed["_requirement_waiver"] = {
        "reason": note,
        "by_user_id": actor_user_id,
        "at": _now().isoformat(),
    }
    row.reviewed_fields_json = reviewed
    _append_waiver_to_decision_basis(
        review, document_key=key, reason=note, actor_user_id=actor_user_id
    )
    await db.flush()
    await _audit_verification(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        review=review,
        document_key=key,
        action="requirement_waived",
        payload={"reason": note[:500]},
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
    key = str(document_key or "").strip()
    file_optional = key in DATA_ONLY_VERIFICATION_KEYS or key in OPTIONAL_FILE_VERIFICATION_KEYS
    if not row.document_id and not file_optional:
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
