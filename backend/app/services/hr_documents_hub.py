"""HR Documents Hub read-model: all linked HR document contexts for the workspace."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.models.workforce_compliance_state import WorkforceComplianceState
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_document_context import WorkforceHrDocumentContext
from backend.app.models.workforce_work_eligibility_payment_requirement import (
    WorkforceWorkEligibilityPaymentRequirement,
)
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.hr_documents_queue import (
    HR_HIGH_RISK_DOC_TYPES,
    _expiring_recommended,
    _missing_recommended,
    _snapshot_summary,
)

MAX_SCAN = 5000


def _handoff_id_from_employee_meta(meta: dict[str, Any] | None) -> str | None:
    if not meta or not isinstance(meta, dict):
        return None
    raw = meta.get("internal_hr_handoff_id")
    s = str(raw).strip() if raw is not None else ""
    return s or None


def _doc_status_str(doc: Document) -> str:
    st = getattr(doc, "status", None)
    if hasattr(st, "value"):
        return str(st.value)
    return str(st or "").lower()


def _risk_for_type(doc_type: str) -> str:
    return "high" if normalize_doc_type(doc_type) in HR_HIGH_RISK_DOC_TYPES else "normal"


def _expires_at_iso(
    *,
    ctx_expires_at: datetime | None,
    doc_expire_date: date | None,
) -> str | None:
    if ctx_expires_at is not None:
        if hasattr(ctx_expires_at, "isoformat"):
            return ctx_expires_at.isoformat()
    if doc_expire_date is not None:
        return doc_expire_date.isoformat()
    return None


def _effective_expire_date(doc: Document, ctx_expires_at: datetime | None) -> date | None:
    if doc.expire_date is not None:
        return doc.expire_date
    if ctx_expires_at is not None:
        if isinstance(ctx_expires_at, datetime):
            return ctx_expires_at.date()
    return None


def _verification_status_display(*, ctx: WorkforceHrDocumentContext) -> str | None:
    vs = (ctx.verification_status or "").strip() or None
    if vs:
        return vs
    if ctx.verified:
        return "verified"
    return None


def _assignee_team_scope(assignee_scope: str, viewer_role: str) -> bool:
    scope = (assignee_scope or "mine").strip().lower()
    role = (viewer_role or "").strip().lower()
    if scope == "team" and role in (
        "administrator",
        "supervisor",
        "hr_officer",
        "superadmin",
    ):
        return True
    return False


def _hub_recommended_action(
    *,
    missing: bool,
    expired: bool,
    expiring: bool,
    risk: str,
) -> str:
    if missing:
        return _missing_recommended(risk=risk)
    if expired:
        return _expiring_recommended(expired=True)
    if expiring:
        return _expiring_recommended(expired=False)
    return "review_document_status"


async def list_hr_documents_hub(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    document_type: str | None,
    legal_category: str | None,
    employee_id_substr: str | None,
    horizon_days: int,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    tid = str(tenant_id).strip()
    hz = max(7, min(int(horizon_days or 30), 90))
    today = datetime.now(timezone.utc).date()
    horizon_end = today + timedelta(days=hz)

    stmt = (
        select(WorkforceHrDocumentContext, WorkforceEmployee, Document, WorkforceComplianceState)
        .join(WorkforceEmployee, WorkforceEmployee.id == WorkforceHrDocumentContext.employee_id)
        .join(Document, Document.id == WorkforceHrDocumentContext.document_id)
        .outerjoin(
            WorkforceComplianceState,
            (WorkforceComplianceState.employee_id == WorkforceEmployee.id)
            & (WorkforceComplianceState.tenant_id == tid),
        )
        .where(
            WorkforceHrDocumentContext.tenant_id == tid,
            WorkforceEmployee.tenant_id == tid,
            Document.tenant_id == tid,
            Document.deleted_at.is_(None),
        )
        .order_by(WorkforceHrDocumentContext.updated_at.desc())
        .limit(MAX_SCAN)
    )
    wanted_doc_type: str | None = None
    if document_type:
        wanted_doc_type = normalize_doc_type(document_type)
    if legal_category:
        lc = str(legal_category).strip()
        if lc:
            stmt = stmt.where(WorkforceHrDocumentContext.legal_category == lc)
    if employee_id_substr:
        sub = str(employee_id_substr).strip()
        if sub:
            stmt = stmt.where(WorkforceEmployee.id.contains(sub))

    res = await db.execute(stmt)
    pairs = res.all()

    handoff_ids: set[str] = set()
    for ctx, emp, _doc, _cs in pairs:
        hid = _handoff_id_from_employee_meta(emp.meta if isinstance(emp.meta, dict) else None)
        if hid:
            handoff_ids.add(hid)

    handoff_by_id: dict[str, CandidateHandoff] = {}
    hid_list = list(handoff_ids)
    if hid_list:
        ho_rows = await db.execute(
            select(CandidateHandoff).where(
                CandidateHandoff.id.in_(hid_list),
                CandidateHandoff.agency_tenant_id == tid,
                CandidateHandoff.destination == "internal_hr",
                CandidateHandoff.status == "accepted",
            )
        )
        for h in ho_rows.scalars().all():
            handoff_by_id[str(h.id)] = h

    snap_by_hid: dict[str, CandidateHandoffSnapshot] = {}
    if hid_list:
        sn_rows = await db.execute(
            select(CandidateHandoffSnapshot).where(CandidateHandoffSnapshot.handoff_id.in_(hid_list))
        )
        for s in sn_rows.scalars().all():
            snap_by_hid[str(s.handoff_id)] = s

    doc_ids = [str(d.id) for _c, _e, d, _cs in pairs]
    pay_by_doc: dict[str, list[str]] = {}
    if doc_ids:
        pr = await db.execute(
            select(WorkforceWorkEligibilityPaymentRequirement).where(
                WorkforceWorkEligibilityPaymentRequirement.tenant_id == tid,
                WorkforceWorkEligibilityPaymentRequirement.receipt_document_id.in_(doc_ids),
            )
        )
        for p in pr.scalars().all():
            rid = str(p.receipt_document_id or "").strip()
            if not rid:
                continue
            pay_by_doc.setdefault(rid, []).append(str(p.id))

    team = _assignee_team_scope(assignee_scope, viewer_role)
    viewer = str(viewer_id).strip()

    rows_out: list[dict[str, Any]] = []
    for ctx, emp, doc, compliance in pairs:
        if wanted_doc_type and normalize_doc_type(str(doc.doc_type or "")) != wanted_doc_type:
            continue
        hid = _handoff_id_from_employee_meta(emp.meta if isinstance(emp.meta, dict) else None)
        ho = handoff_by_id.get(hid) if hid else None
        assignee = str(ho.assigned_to_user_id).strip() if ho and ho.assigned_to_user_id else None
        if not team and assignee and assignee != viewer:
            continue

        canon = normalize_doc_type(str(doc.doc_type or ""))
        st = _doc_status_str(doc)
        risk = _risk_for_type(canon)
        exp_date = _effective_expire_date(doc, ctx.expires_at)
        expired = bool(
            exp_date is not None
            and (exp_date < today or st == DocumentStatus.expired.value)
        )
        expiring = bool(
            not expired
            and exp_date is not None
            and today <= exp_date <= horizon_end
        )
        missing = st == DocumentStatus.missing.value

        snap = snap_by_hid.get(hid) if hid else None
        payload = dict(snap.payload) if snap is not None and isinstance(snap.payload, dict) else None

        expires_iso = _expires_at_iso(ctx_expires_at=ctx.expires_at, doc_expire_date=doc.expire_date)
        vs_disp = _verification_status_display(ctx=ctx)

        rows_out.append(
            {
                "employee_id": str(emp.id),
                "employee_name": str(emp.display_name or "").strip() or str(emp.id),
                "handoff_id": hid,
                "document_id": str(doc.id),
                "document_type": canon,
                "legal_category": ctx.legal_category,
                "document_group": ctx.document_group,
                "context_type": str(ctx.context_type or ""),
                "required": bool(ctx.required),
                "verification_status": vs_disp,
                "current_status": st,
                "expires_at": expires_iso,
                "risk": risk,
                "source": ctx.source or (doc.source if getattr(doc, "source", None) else None),
                "missing": missing,
                "expired": expired,
                "expiring": expiring,
                "recommended_action": _hub_recommended_action(
                    missing=missing, expired=expired, expiring=expiring, risk=risk
                ),
                "compliance_status": compliance.status if compliance else None,
                "compliance_cannot_work": bool(compliance.cannot_work) if compliance else None,
                "handoff_snapshot_summary": _snapshot_summary(payload),
                "assignee_user_id": assignee,
                "work_eligibility_payment_requirement_ids": pay_by_doc.get(str(doc.id), []),
            }
        )

    total = len(rows_out)
    page = rows_out[offset : offset + limit]
    return page, total
