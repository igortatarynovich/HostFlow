"""HR employee operational profile read-model (single GET for the employee workspace UI)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx
from backend.app.models.audit import ActivityLog as ActivityLogModel
from backend.app.models.company import Company
from backend.app.models.own_company import OwnCompany
from backend.app.models.user import User
from backend.app.models.vacancy import Vacancy
from backend.app.services.hr_documents_queue import list_hr_documents_expiring, list_hr_documents_missing
from backend.app.services.hr_operational_risk import list_operational_risk_items
from backend.app.services.workforce_directory import (
    _assigned_hr_user_id,
    _compliance_and_risk,
    _full_name_from_employee,
    _handoff_id_from_meta,
    _position_from_employment,
    _rank_from_severity,
)
from backend.app.services import workforce_employees as we_svc

_logger = logging.getLogger(__name__)

_QUEUE_LIMIT = 4000


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _employment_is_active(*, start_date: date | None, end_date: date | None, today: date) -> bool:
    if start_date and start_date > today:
        return False
    if end_date and end_date < today:
        return False
    return True


def _recruiter_summary(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    return {
        "captured_at": snapshot.get("captured_at"),
        "candidate_id": snapshot.get("candidate_id"),
        "first_name": snapshot.get("first_name"),
        "last_name": snapshot.get("last_name"),
        "email": snapshot.get("email"),
        "phone": snapshot.get("phone"),
        "stage": snapshot.get("stage"),
        "status": snapshot.get("status"),
    }


async def collect_operational_profile_raw(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer: UserCtx,
    employee_id: str,
) -> dict[str, Any] | None:
    """Returns ORM rows and plain dicts for the router to serialize. None if employee missing."""
    tid = str(tenant_id).strip()
    eid = str(employee_id).strip()
    emp = await we_svc.get_employee(db, tid, eid)
    if not emp:
        return None

    bundle = await we_svc.get_hr_bundle(db, tid, eid)
    employments = list(bundle.get("employments") or [])
    latest = employments[0] if employments else None

    own_name: str | None = None
    if emp.own_company_id:
        oc = (await db.execute(select(OwnCompany).where(OwnCompany.id == str(emp.own_company_id)))).scalar_one_or_none()
        if oc:
            own_name = str(oc.name or "").strip() or str(oc.id)

    client_name: str | None = None
    if emp.company_id:
        c = (await db.execute(select(Company).where(Company.id == str(emp.company_id)))).scalar_one_or_none()
        if c:
            client_name = str(c.name or "").strip() or str(c.id)

    vac_title: str | None = None
    vac_id = str(latest.vacancy_id) if latest and latest.vacancy_id else None
    if not vac_id and emp.vacancy_id:
        vac_id = str(emp.vacancy_id)
    if vac_id:
        v = (await db.execute(select(Vacancy).where(Vacancy.id == vac_id))).scalar_one_or_none()
        if v:
            vac_title = str(v.title or "").strip() or str(v.id)

    position = _position_from_employment(latest, vac_title)
    start_d: date | None = None
    if latest and latest.start_date:
        start_d = latest.start_date
    elif emp.hire_date:
        start_d = emp.hire_date

    meta = emp.meta if isinstance(emp.meta, dict) else {}
    aid = _assigned_hr_user_id(meta, str(emp.recruiter_user_id) if emp.recruiter_user_id else None)
    assigned_label: str | None = None
    if aid:
        u = (await db.execute(select(User).where(User.id == aid))).scalar_one_or_none()
        if u:
            assigned_label = (u.full_name or "").strip() or (u.email or "").strip() or str(u.id)

    viewer_id = str(viewer.sub).strip()
    viewer_role = str(viewer.role or "").strip().lower()

    missing_items: list[dict[str, Any]] = []
    expiring_items: list[dict[str, Any]] = []
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
            limit=_QUEUE_LIMIT,
            offset=0,
        )
        missing_items = [r for r in miss_rows if str(r.get("workforce_employee_id") or "") == eid]
    except Exception:
        _logger.exception("operational_profile: list_hr_documents_missing failed tenant=%s", tid)

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
                limit=_QUEUE_LIMIT,
                offset=0,
            )
            for r in exp_rows:
                if str(r.get("workforce_employee_id") or "") == eid:
                    expiring_items.append(r)
    except Exception:
        _logger.exception("operational_profile: list_hr_documents_expiring failed tenant=%s", tid)

    missing_n = len(missing_items)
    expiring_n = len(expiring_items)

    worst = 0
    risk_items: list[dict[str, Any]] = []
    try:
        all_risks = await list_operational_risk_items(
            db,
            tenant_id=tid,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            assignee_scope="team",
            horizon_days=30,
            handoff_id=None,
            candidate_id=None,
        )
        for it in all_risks:
            if str(it.get("workforce_employee_id") or "") != eid:
                continue
            risk_items.append(it)
            worst = max(worst, _rank_from_severity(str(it.get("severity") or "")))
    except Exception:
        _logger.exception("operational_profile: list_operational_risk_items failed tenant=%s", tid)

    comp_st, risk_lv = _compliance_and_risk(
        employee_status=str(emp.status or ""),
        missing_n=missing_n,
        expiring_n=expiring_n,
        worst_severity=worst,
    )

    handoff_by_name: str | None = None
    if emp.handoff_by_user_id:
        u = (await db.execute(select(User).where(User.id == str(emp.handoff_by_user_id)))).scalar_one_or_none()
        if u:
            handoff_by_name = (u.full_name or "").strip() or (u.email or "").strip() or str(u.id)

    snap = emp.candidate_snapshot if isinstance(emp.candidate_snapshot, dict) else None

    today = _utc_today()
    overdue = 0
    for t in bundle.get("onboarding_tasks") or []:
        st = str(getattr(t, "status", "") or "").lower()
        if st == "done":
            continue
        due = getattr(t, "due_at", None)
        if due is not None:
            d = due.date() if hasattr(due, "date") else due
            if isinstance(d, datetime):
                d = d.date()
            if isinstance(d, date) and d < today:
                overdue += 1

    alerts: list[dict[str, str]] = []
    if comp_st == "blocked":
        alerts.append({"code": "compliance_blocked", "message": "Operational risk requires attention before proceeding."})
    if missing_n:
        alerts.append({"code": "missing_documents", "message": f"{missing_n} required document(s) missing."})
    if expiring_n:
        alerts.append({"code": "expiring_documents", "message": f"{expiring_n} document(s) expiring or expired."})
    if overdue:
        alerts.append({"code": "onboarding_overdue", "message": f"{overdue} onboarding task(s) overdue."})
    for ri in risk_items[:5]:
        alerts.append(
            {
                "code": str(ri.get("risk_code") or "risk"),
                "message": str(ri.get("reason") or ri.get("risk_code") or "Risk"),
            }
        )

    timeline: list[dict[str, Any]] = []

    def _iso(dt: Any) -> str | None:
        if dt is None:
            return None
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        return str(dt)

    timeline.append(
        {
            "id": f"evt-emp-created-{eid}",
            "occurred_at": _iso(emp.created_at) or "",
            "kind": "employee",
            "title": "Employee record created",
            "detail": None,
            "actor_id": None,
        }
    )
    if emp.handoff_at:
        timeline.append(
            {
                "id": f"evt-handoff-{eid}",
                "occurred_at": _iso(emp.handoff_at) or "",
                "kind": "handoff",
                "title": "Handoff recorded on employee",
                "detail": handoff_by_name,
                "actor_id": str(emp.handoff_by_user_id) if emp.handoff_by_user_id else None,
            }
        )

    for em in employments:
        sd = getattr(em, "start_date", None)
        ed = getattr(em, "end_date", None)
        timeline.append(
            {
                "id": f"evt-emp-contract-{em.id}",
                "occurred_at": _iso(getattr(em, "created_at", None)) or "",
                "kind": "employment",
                "title": f"Employment / contract ({getattr(em, 'contract_type', '') or '—'})",
                "detail": f"{sd.isoformat() if sd else '—'} → {ed.isoformat() if ed else 'open'}",
                "actor_id": None,
            }
        )

    for task in bundle.get("onboarding_tasks") or []:
        if str(getattr(task, "status", "") or "").lower() == "done" and getattr(task, "completed_at", None):
            timeline.append(
                {
                    "id": f"evt-task-done-{task.id}",
                    "occurred_at": _iso(task.completed_at) or "",
                    "kind": "onboarding",
                    "title": f"Onboarding: {getattr(task, 'title', 'Task')}",
                    "detail": "Completed",
                    "actor_id": None,
                }
            )

    ors: list[Any] = [
        and_(ActivityLogModel.target_type == "workforce_employee", ActivityLogModel.target_id == eid),
    ]
    for em in employments:
        ors.append(
            and_(ActivityLogModel.target_type == "workforce_employment", ActivityLogModel.target_id == str(em.id))
        )
    pp = bundle.get("payroll_profile")
    if pp is not None:
        ors.append(
            and_(
                ActivityLogModel.target_type == "workforce_payroll_profile",
                ActivityLogModel.target_id == str(pp.id),
            )
        )
    zp = bundle.get("zus_profile")
    if zp is not None:
        ors.append(
            and_(ActivityLogModel.target_type == "workforce_zus_profile", ActivityLogModel.target_id == str(zp.id))
        )
    for task in bundle.get("onboarding_tasks") or []:
        ors.append(
            and_(
                ActivityLogModel.target_type == "workforce_onboarding_task",
                ActivityLogModel.target_id == str(task.id),
            )
        )
    for ab in bundle.get("absences") or []:
        ors.append(and_(ActivityLogModel.target_type == "workforce_absence", ActivityLogModel.target_id == str(ab.id)))
    for lv in bundle.get("leave_requests") or []:
        ors.append(
            and_(ActivityLogModel.target_type == "workforce_leave_request", ActivityLogModel.target_id == str(lv.id))
        )

    try:
        stmt = (
            select(ActivityLogModel)
            .where(ActivityLogModel.tenant_id == tid, or_(*ors))
            .order_by(ActivityLogModel.created_at.desc())
            .limit(120)
        )
        logs = list((await db.execute(stmt)).scalars().all())
        for log in logs:
            timeline.append(
                {
                    "id": str(log.id),
                    "occurred_at": _iso(log.created_at) or "",
                    "kind": "activity",
                    "title": str(log.action or ""),
                    "detail": (str(log.payload)[:400] + "…") if log.payload else None,
                    "actor_id": str(log.actor_id) if log.actor_id else None,
                }
            )
    except Exception:
        _logger.exception("operational_profile: activity log query failed tenant=%s", tid)

    timeline.sort(key=lambda x: str(x.get("occurred_at") or ""), reverse=True)
    timeline = timeline[:100]

    prob_iso = emp.probation_end.isoformat() if getattr(emp, "probation_end", None) else None

    operational_summary = {
        "employee_status": str(emp.status or ""),
        "full_name": _full_name_from_employee(emp),
        "employer": own_name,
        "client": client_name,
        "position": position,
        "start_date": start_d.isoformat() if start_d else None,
        "probation_end": prob_iso,
        "assigned_hr": assigned_label,
        "assigned_hr_user_id": aid,
        "handoff_id": _handoff_id_from_meta(meta),
        "compliance_status": comp_st,
        "missing_documents_count": missing_n,
        "expiring_documents_count": expiring_n,
        "risk_level": risk_lv,
    }

    transfer = {
        "handoff_id": _handoff_id_from_meta(meta),
        "handoff_at": _iso(emp.handoff_at),
        "handoff_by_user_id": str(emp.handoff_by_user_id) if emp.handoff_by_user_id else None,
        "handoff_by_name": handoff_by_name,
        "candidate_id": str(emp.candidate_id) if emp.candidate_id else None,
        "vacancy_id": str(emp.vacancy_id) if emp.vacancy_id else None,
    }

    employment_ops: list[dict[str, Any]] = []
    for em in employments:
        sd = getattr(em, "start_date", None)
        ed = getattr(em, "end_date", None)
        row_vt = vac_title if latest and str(em.id) == str(latest.id) else None
        is_act = _employment_is_active(start_date=sd, end_date=ed, today=today)
        employment_ops.append(
            {
                "id": str(em.id),
                "contract_type": str(getattr(em, "contract_type", "") or ""),
                "start_date": sd.isoformat() if sd else None,
                "end_date": ed.isoformat() if ed else None,
                "is_active": is_act,
                "probation_end": prob_iso if is_act else None,
                "position": _position_from_employment(em, row_vt),
            }
        )

    return {
        "employee": emp,
        "bundle": bundle,
        "operational_summary": operational_summary,
        "transfer": transfer,
        "recruiter_summary": _recruiter_summary(snap),
        "hire_snapshot": snap,
        "documents_missing": missing_items,
        "documents_expiring": expiring_items,
        "risks": risk_items,
        "alerts": alerts,
        "onboarding_overdue_count": overdue,
        "timeline": timeline,
        "employment_operational": employment_ops,
    }
