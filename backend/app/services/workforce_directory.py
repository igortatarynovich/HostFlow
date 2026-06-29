"""HR Employees Directory read-model (single batch; no per-employee N+1 from the SPA)."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx
from backend.app.models.company import Company
from backend.app.models.own_company import OwnCompany
from backend.app.models.user import User
from backend.app.models.vacancy import Vacancy
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.models.workforce_hr_review import WorkforceHrReview
from backend.app.services.hr_documents_queue import list_hr_documents_expiring, list_hr_documents_missing
from backend.app.services.hr_inbox import _document_verification_counts_by_review
from backend.app.services.hr_operational_risk import list_operational_risk_items

_logger = logging.getLogger(__name__)

_MAX_SCAN = 2000
_MISSING_QUEUE_LIMIT = 4000
_EXPIRING_QUEUE_LIMIT = 4000

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}


def _rank_from_severity(sev: str | None) -> int:
    s = (sev or "").strip().lower()
    return _SEVERITY_RANK.get(s, 0)


def _severity_from_rank(r: int) -> str:
    if r >= _SEVERITY_RANK["critical"]:
        return "critical"
    if r >= _SEVERITY_RANK["high"]:
        return "high"
    if r >= _SEVERITY_RANK["medium"]:
        return "medium"
    if r >= _SEVERITY_RANK["low"]:
        return "low"
    return "none"


def _full_name_from_employee(row: WorkforceEmployee) -> str:
    dn = (row.display_name or "").strip()
    if dn:
        return dn
    snap = row.candidate_snapshot if isinstance(row.candidate_snapshot, dict) else None
    if not snap:
        return "—"
    fn = str(snap.get("first_name") or "").strip()
    ln = str(snap.get("last_name") or "").strip()
    parts = [p for p in (fn, ln) if p]
    return " ".join(parts) if parts else "—"


def _meta_str(meta: dict[str, Any] | None, *keys: str) -> str | None:
    if not meta:
        return None
    for k in keys:
        v = meta.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _position_from_employment(emp: WorkforceEmployment | None, vacancy_title: str | None) -> str | None:
    if not emp:
        return vacancy_title
    m = emp.meta if isinstance(emp.meta, dict) else {}
    for k in ("position", "job_title", "title", "role"):
        v = m.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    if emp.conditions_text and str(emp.conditions_text).strip():
        t = str(emp.conditions_text).strip()
        return t[:120] + ("…" if len(t) > 120 else "")
    return vacancy_title


def _handoff_id_from_meta(meta: dict[str, Any] | None) -> str | None:
    if not meta:
        return None
    hid = meta.get("internal_hr_handoff_id")
    if hid is None:
        return None
    s = str(hid).strip()
    return s or None


def _assigned_hr_user_id(meta: dict[str, Any] | None, recruiter_user_id: str | None) -> str | None:
    if meta:
        v = meta.get("assigned_hr_user_id")
        if v is not None and str(v).strip():
            return str(v).strip()
    return str(recruiter_user_id).strip() if recruiter_user_id else None


def _compliance_and_risk(
    *,
    employee_status: str,
    missing_n: int,
    expiring_n: int,
    worst_severity: int,
) -> tuple[str, str]:
    """(compliance_status, risk_level) for directory row."""
    st = (employee_status or "").strip().lower()
    if st == "suspended":
        return "suspended", _severity_from_rank(worst_severity)

    if worst_severity >= _SEVERITY_RANK["critical"]:
        return "blocked", _severity_from_rank(worst_severity)

    if missing_n > 0:
        return "missing_docs", _severity_from_rank(worst_severity)

    if expiring_n > 0:
        return "expiring_docs", _severity_from_rank(worst_severity)

    return "compliant", _severity_from_rank(worst_severity)


async def list_employees_directory(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer: UserCtx,
    status: Optional[str] = None,
    compliance_status: Optional[str] = None,
    risk_level: Optional[str] = None,
    missing_docs: Optional[bool] = None,
    expiring_docs: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    tid = str(tenant_id).strip()
    lim = max(1, min(int(limit or 50), 200))
    off = max(0, int(offset or 0))

    stmt = select(WorkforceEmployee).where(WorkforceEmployee.tenant_id == tid)
    if status:
        stmt = stmt.where(WorkforceEmployee.status == str(status).strip())
    q = (search or "").strip()
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(WorkforceEmployee.display_name).like(like))
    stmt = stmt.order_by(WorkforceEmployee.created_at.desc()).limit(_MAX_SCAN)
    emp_rows = list((await db.execute(stmt)).scalars().all())
    if not emp_rows:
        return [], 0

    emp_ids = [str(e.id) for e in emp_rows]

    emps_all = (
        (
            await db.execute(
                select(WorkforceEmployment)
                .where(
                    WorkforceEmployment.tenant_id == tid,
                    WorkforceEmployment.employee_id.in_(emp_ids),
                )
                .order_by(
                    WorkforceEmployment.employee_id.asc(),
                    WorkforceEmployment.created_at.desc(),
                )
            )
        )
        .scalars()
        .all()
    )
    latest_emp: dict[str, WorkforceEmployment] = {}
    for r in emps_all:
        eid = str(r.employee_id)
        if eid not in latest_emp:
            latest_emp[eid] = r

    own_ids = {str(e.own_company_id) for e in emp_rows if e.own_company_id}
    company_ids = {str(e.company_id) for e in emp_rows if e.company_id}
    vacancy_ids: set[str] = set()
    for e in latest_emp.values():
        if e.vacancy_id:
            vacancy_ids.add(str(e.vacancy_id))

    own_names: dict[str, str] = {}
    if own_ids:
        rows = (await db.execute(select(OwnCompany).where(OwnCompany.id.in_(list(own_ids))))).scalars().all()
        for oc in rows:
            own_names[str(oc.id)] = str(oc.name or "").strip() or str(oc.id)

    client_names: dict[str, str] = {}
    if company_ids:
        rows = (await db.execute(select(Company).where(Company.id.in_(list(company_ids))))).scalars().all()
        for c in rows:
            client_names[str(c.id)] = str(c.name or "").strip() or str(c.id)

    vacancy_titles: dict[str, str] = {}
    if vacancy_ids:
        rows = (await db.execute(select(Vacancy).where(Vacancy.id.in_(list(vacancy_ids))))).scalars().all()
        for v in rows:
            vacancy_titles[str(v.id)] = str(v.title or "").strip() or str(v.id)

    user_ids: set[str] = set()
    for e in emp_rows:
        if e.recruiter_user_id:
            user_ids.add(str(e.recruiter_user_id))
        m = e.meta if isinstance(e.meta, dict) else {}
        aid = _assigned_hr_user_id(m, e.recruiter_user_id)
        if aid:
            user_ids.add(aid)

    user_labels: dict[str, str] = {}
    if user_ids:
        rows = (await db.execute(select(User).where(User.id.in_(list(user_ids))))).scalars().all()
        for u in rows:
            label = (u.full_name or "").strip() or (u.email or "").strip() or str(u.id)
            user_labels[str(u.id)] = label

    viewer_id = str(viewer.sub).strip()
    viewer_role = str(viewer.role or "").strip().lower()

    missing_by_wf: dict[str, int] = defaultdict(int)
    try:
        miss_rows, _ = await list_hr_documents_missing(
            db,
            tenant_id=tid,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            assignee_scope="team",
            document_type=None,
            priority=None,
            handoff_id=None,
            candidate_id=None,
            limit=_MISSING_QUEUE_LIMIT,
            offset=0,
        )
        for r in miss_rows:
            wid = r.get("workforce_employee_id")
            if wid:
                missing_by_wf[str(wid)] += 1
    except Exception:
        _logger.exception("directory: list_hr_documents_missing failed tenant=%s", tid)

    expiring_by_wf: dict[str, int] = defaultdict(int)
    try:
        for status_f in ("expiring", "expired"):
            exp_rows, _ = await list_hr_documents_expiring(
                db,
                tenant_id=tid,
                viewer_id=viewer_id,
                viewer_role=viewer_role,
                assignee_scope="team",
                horizon_days=30,
                status=status_f,
                document_type=None,
                risk=None,
                handoff_id=None,
                candidate_id=None,
                limit=_EXPIRING_QUEUE_LIMIT,
                offset=0,
            )
            for r in exp_rows:
                wid = r.get("workforce_employee_id")
                if wid:
                    expiring_by_wf[str(wid)] += 1
    except Exception:
        _logger.exception("directory: list_hr_documents_expiring failed tenant=%s", tid)

    worst_risk_by_wf: dict[str, int] = defaultdict(int)
    try:
        risk_items = await list_operational_risk_items(
            db,
            tenant_id=tid,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            assignee_scope="team",
            horizon_days=30,
            handoff_id=None,
            candidate_id=None,
        )
        for it in risk_items:
            wid = it.get("workforce_employee_id")
            if not wid:
                continue
            w = str(wid)
            rk = _rank_from_severity(str(it.get("severity") or ""))
            if rk > worst_risk_by_wf[w]:
                worst_risk_by_wf[w] = rk
    except Exception:
        _logger.exception("directory: list_operational_risk_items failed tenant=%s", tid)

    reviews_by_emp: dict[str, WorkforceHrReview] = {}
    if emp_ids:
        review_rows = (
            await db.execute(
                select(WorkforceHrReview).where(
                    WorkforceHrReview.tenant_id == tid,
                    WorkforceHrReview.employee_id.in_(emp_ids),
                )
            )
        ).scalars().all()
        for rev in review_rows:
            if rev.employee_id:
                reviews_by_emp[str(rev.employee_id)] = rev
    review_ids = [str(r.id) for r in reviews_by_emp.values() if r.id]
    doc_counts = await _document_verification_counts_by_review(db, tenant_id=tid, review_ids=review_ids)

    rows_out: list[dict[str, Any]] = []
    for e in emp_rows:
        eid = str(e.id)
        meta = e.meta if isinstance(e.meta, dict) else {}
        le = latest_emp.get(eid)
        vac_title = vacancy_titles.get(str(le.vacancy_id)) if le and le.vacancy_id else None
        position = _position_from_employment(le, vac_title)
        start_date: date | None = None
        if le and le.start_date:
            start_date = le.start_date
        elif e.hire_date:
            start_date = e.hire_date

        employer = own_names.get(str(e.own_company_id)) if e.own_company_id else None
        client = client_names.get(str(e.company_id)) if e.company_id else None

        missing_n = int(missing_by_wf.get(eid, 0))
        expiring_n = int(expiring_by_wf.get(eid, 0))
        worst = int(worst_risk_by_wf.get(eid, 0))
        comp_st, risk_lv = _compliance_and_risk(
            employee_status=str(e.status or ""),
            missing_n=missing_n,
            expiring_n=expiring_n,
            worst_severity=worst,
        )

        aid = _assigned_hr_user_id(meta, str(e.recruiter_user_id) if e.recruiter_user_id else None)
        assigned_label = user_labels.get(aid) if aid else None

        review = reviews_by_emp.get(eid)
        hr_review_status = str(review.status) if review else None
        verified_n, total_n = (None, None)
        if review and review.id:
            counts = doc_counts.get(str(review.id))
            if counts:
                verified_n, total_n = counts

        row = {
            "employee_id": eid,
            "full_name": _full_name_from_employee(e),
            "status": str(e.status or ""),
            "employer": employer,
            "client": client,
            "position": position,
            "start_date": start_date.isoformat() if start_date else None,
            "assigned_hr": assigned_label,
            "assigned_hr_user_id": aid,
            "handoff_id": _handoff_id_from_meta(meta),
            "candidate_id": str(e.candidate_id) if e.candidate_id else None,
            "compliance_status": comp_st,
            "missing_documents_count": missing_n,
            "expiring_documents_count": expiring_n,
            "risk_level": risk_lv,
            "hr_review_status": hr_review_status,
            "documents_verified_count": verified_n,
            "documents_total_count": total_n,
        }

        if compliance_status and str(compliance_status).strip().lower() != str(row["compliance_status"]).lower():
            continue
        if risk_level and str(risk_level).strip().lower() != str(row["risk_level"]).lower():
            continue
        if missing_docs is True and row["missing_documents_count"] <= 0:
            continue
        if expiring_docs is True and row["expiring_documents_count"] <= 0:
            continue

        rows_out.append(row)

    total = len(rows_out)
    page = rows_out[off : off + lim]
    return page, total
