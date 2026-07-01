"""HR employee operational profile read-model (single GET for the employee workspace UI)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx
from backend.app.models.audit import ActivityLog as ActivityLogModel
from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.own_company import OwnCompany
from backend.app.models.user import User
from backend.app.models.vacancy import Vacancy
from backend.app.services.hr_documents_queue import list_hr_documents_expiring, list_hr_documents_missing
from backend.app.services.hr_document_control_tasks import list_document_control_tasks
from backend.app.services.hr_expected_documents import load_hr_expected_documents
from backend.app.services.reference_service_facade import ReferenceContext, ReferenceServiceFacade
from backend.app.services.hr_operational_risk import list_operational_risk_items
from backend.app.services.workforce_eligibility_delivery_contract import (
    WorkforceEligibilityContext,
    resolve_workforce_eligibility_via_contract,
)
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


def _map_applicability_to_expected_docs(
    rows: list[dict[str, Any]],
    *,
    work_country: str | None,
    citizenship: str | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("document_code") or "").strip()
        if not code:
            continue
        group = str(row.get("group") or "other").strip() or "other"
        expiry_rules = row.get("expiry_rules") if isinstance(row.get("expiry_rules"), dict) else {}
        verification_profile = (
            row.get("verification_profile") if isinstance(row.get("verification_profile"), dict) else {}
        )
        out.append(
            {
                "document_code": code,
                "label": str(row.get("label") or code),
                "group": group,
                "default_owner": "HR",
                "requires_expiry": bool(
                    expiry_rules.get("expiry_required") or expiry_rules.get("has_expiry")
                ),
                "verification_required": bool(
                    verification_profile.get("manual_review_required", True)
                ),
                "applies_to_driver": True,
                "applies_to_non_driver": True,
                "blocks_employment": bool(row.get("required")),
                "renewal_window_days": int(expiry_rules.get("renewal_window_days") or 30),
                "default_next_action": str(row.get("due_point") or "before_employment"),
                "aliases": [code],
                "source": "packs",
                "source_pack": row.get("source_pack"),
                "reason": row.get("reason"),
                "criticality": row.get("criticality"),
                "tenant_override_changed": bool(row.get("tenant_override_changed")),
                "context": {
                    "work_country": work_country,
                    "citizenship": citizenship,
                },
            }
        )
    return out


def _recruiter_summary(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    out = {
        "captured_at": snapshot.get("captured_at"),
        "candidate_id": snapshot.get("candidate_id"),
        "first_name": snapshot.get("first_name"),
        "last_name": snapshot.get("last_name"),
        "email": snapshot.get("email"),
        "phone": snapshot.get("phone"),
        "stage": snapshot.get("stage"),
        "status": snapshot.get("status"),
        "citizenship": snapshot.get("citizenship"),
        "work_country": snapshot.get("work_country"),
        "legal_status": snapshot.get("legal_status"),
        "position_category": snapshot.get("position_category"),
        "vacancy_context": snapshot.get("vacancy_context"),
        "notes": snapshot.get("notes"),
        "document_field_values": snapshot.get("document_field_values"),
        "personal_data": snapshot.get("personal_data"),
        "contacts": snapshot.get("contacts"),
        "hr_identity": snapshot.get("hr_identity"),
    }
    return {k: v for k, v in out.items() if v is not None}


def _build_employee_dossier(
    *,
    employee: Any,
    recruiter_summary: dict[str, Any],
    bundle: dict[str, Any],
    documents_missing: list[dict[str, Any]],
    documents_expiring: list[dict[str, Any]],
    onboarding_overdue: int,
) -> dict[str, Any]:
    """Structured employee file used by HR as the primary dossier surface."""
    personal = recruiter_summary.get("personal_data") if isinstance(recruiter_summary, dict) else {}
    hr_identity = recruiter_summary.get("hr_identity") if isinstance(recruiter_summary, dict) else {}
    if not isinstance(personal, dict):
        personal = {}
    if not isinstance(hr_identity, dict):
        hr_identity = {}
    wel = bundle.get("work_eligibility_profile")
    ctx = (bundle.get("hr_document_context_summary") or {}).get("items") or []
    now = datetime.now(timezone.utc).date()

    expiring_soon = 0
    expired = 0
    for item in ctx:
        exp = getattr(item, "expires_at", None)
        if exp is None:
            continue
        d = exp.date() if hasattr(exp, "date") else None
        if d is None:
            continue
        if d < now:
            expired += 1
        elif (d - now).days <= 30:
            expiring_soon += 1

    quals = []
    for key, label in (
        ("license_number", "driver_license"),
        ("code95_number", "code95"),
        ("tacho_card_number", "tachograph_card"),
        ("passport_number", "passport"),
        ("residence_card_number", "residence_card"),
        ("work_permit_number", "work_permit"),
    ):
        value = (recruiter_summary.get("document_field_values") or {}).get(key)
        if value:
            quals.append({"code": label, "value": str(value)})

    actions: list[dict[str, Any]] = []
    if documents_missing:
        actions.append({"code": "documents_missing", "priority": "high", "count": len(documents_missing)})
    if documents_expiring:
        actions.append({"code": "documents_expiring", "priority": "medium", "count": len(documents_expiring)})
    if onboarding_overdue > 0:
        actions.append({"code": "onboarding_overdue", "priority": "high", "count": onboarding_overdue})
    if wel is not None:
        st = str(getattr(wel, "eligibility_status", "") or "").strip().lower()
        if st in ("blocked", "missing_data", "not_evaluated"):
            actions.append({"code": "work_eligibility_attention", "priority": "high", "status": st})

    return {
        "identity": {
            "display_name": str(getattr(employee, "display_name", "") or "").strip() or None,
            "first_name": recruiter_summary.get("first_name"),
            "last_name": recruiter_summary.get("last_name"),
            "legal_name": hr_identity.get("legal_name") or personal.get("legal_name"),
            "email": hr_identity.get("email") or recruiter_summary.get("email"),
            "phone": hr_identity.get("phone") or recruiter_summary.get("phone"),
            "birth_date": hr_identity.get("birth_date") or personal.get("birth_date"),
            "citizenship": hr_identity.get("citizenship") or recruiter_summary.get("citizenship"),
            "address": hr_identity.get("address") or personal.get("address"),
            "pesel": hr_identity.get("pesel") or personal.get("pesel"),
            "passport_number": hr_identity.get("passport_number") or personal.get("passport_number"),
            "passport_expiry": (
                hr_identity.get("passport_expiry")
                or personal.get("passport_expiry")
                or personal.get("passport_valid_to")
            ),
            "driver_license_number": (
                hr_identity.get("driver_license_number")
                or personal.get("driver_license_number")
                or personal.get("license_number")
            ),
            "driver_license_expiry": (
                hr_identity.get("driver_license_expiry")
                or personal.get("driver_license_expiry")
                or personal.get("driver_license_valid_to")
                or personal.get("license_valid_to")
            ),
            "code95_expiry": (
                hr_identity.get("code95_expiry")
                or personal.get("code95_expiry")
                or personal.get("code_95_expiry")
            ),
            "tachograph_expiry": (
                hr_identity.get("tachograph_expiry")
                or personal.get("tachograph_expiry")
                or personal.get("tachograph_card_expiry")
                or personal.get("tacho_card_expiry")
            ),
            "medical_expiry": (
                hr_identity.get("medical_expiry")
                or personal.get("medical_expiry")
                or personal.get("medical_valid_to")
                or personal.get("medical_exam_expiry")
            ),
        },
        "legal": {
            "work_country": recruiter_summary.get("work_country") or getattr(wel, "work_country", None),
            "legal_status": recruiter_summary.get("legal_status") or getattr(wel, "residence_status", None),
            "eligibility_status": getattr(wel, "eligibility_status", None),
            "requires_work_permit": getattr(wel, "requires_work_permit", None),
            "work_permit_valid_to": (
                getattr(wel, "work_permit_valid_to", None).isoformat()
                if getattr(wel, "work_permit_valid_to", None)
                else None
            ),
            "legal_stay_valid_to": (
                getattr(wel, "legal_stay_valid_to", None).isoformat()
                if getattr(wel, "legal_stay_valid_to", None)
                else None
            ),
        },
        "documents": {
            "linked_total": int((bundle.get("hr_document_context_summary") or {}).get("total") or 0),
            "missing_total": len(documents_missing),
            "expiring_total": len(documents_expiring),
            "expired_total": expired,
            "expiring_30d_total": expiring_soon,
        },
        "qualifications": {
            "items": quals,
        },
        "employment": {
            "status": str(getattr(employee, "status", "") or ""),
            "hire_date": getattr(employee, "hire_date", None).isoformat() if getattr(employee, "hire_date", None) else None,
            "termination_date": (
                getattr(employee, "termination_date", None).isoformat()
                if getattr(employee, "termination_date", None)
                else None
            ),
            "contracts_total": len(bundle.get("employments") or []),
            "absences_total": len(bundle.get("absences") or []),
            "leave_requests_total": len(bundle.get("leave_requests") or []),
            "onboarding_open_total": len(
                [x for x in (bundle.get("onboarding_tasks") or []) if str(getattr(x, "status", "")).lower() != "done"]
            ),
        },
        "next_actions": actions,
    }


async def _enrich_snapshot_from_candidate_if_needed(
    db: AsyncSession,
    *,
    employee: Any,
    snapshot: dict[str, Any] | None,
) -> dict[str, Any] | None:
    snap = dict(snapshot) if isinstance(snapshot, dict) else None
    if not snap:
        return snap
    hr_identity = snap.get("hr_identity")
    has_identity = isinstance(hr_identity, dict) and any(v not in (None, "") for v in hr_identity.values())
    if has_identity:
        return snap
    candidate_id = str(getattr(employee, "candidate_id", "") or "").strip()
    if not candidate_id:
        return snap
    cand = (await db.execute(select(Candidate).where(Candidate.id == candidate_id))).scalar_one_or_none()
    if not cand:
        return snap
    fresh = we_svc._candidate_snapshot(cand)
    merged = dict(snap)
    for key in (
        "hr_identity",
        "personal_data",
        "contacts",
        "extra",
        "citizenship",
        "work_country",
        "legal_status",
        "position_category",
        "document_field_values",
        "vacancy_context",
    ):
        if merged.get(key) in (None, "", {}):
            merged[key] = fresh.get(key)
    return merged


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
    snap = await _enrich_snapshot_from_candidate_if_needed(db, employee=emp, snapshot=snap)

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

    wel = bundle.get("work_eligibility_profile")
    work_country = (
        str(getattr(wel, "work_country", "") or "").strip()
        or str((snap or {}).get("work_country") or "").strip()
        or None
    )
    citizenship = (
        str(getattr(wel, "citizenship", "") or "").strip()
        or str((snap or {}).get("citizenship") or "").strip()
        or None
    )
    position_category = (
        str(getattr(wel, "position_category", "") or "").strip()
        or str((snap or {}).get("position_category") or "").strip()
        or None
    )

    expected_docs_app = await ReferenceServiceFacade.get_applicable_documents(
        db,
        context=ReferenceContext(
            tenant_id=tid,
            module="hr",
            entity_type="employee",
            entity_id=eid,
            employee_id=eid,
            candidate_id=str(emp.candidate_id) if emp.candidate_id else None,
            work_country=work_country,
            citizenship=citizenship,
            position_category=position_category,
            stage="hr",
            client_id=str(emp.company_id) if emp.company_id else None,
            vacancy_id=vac_id,
        ),
    )
    expected_docs = _map_applicability_to_expected_docs(
        expected_docs_app,
        work_country=work_country,
        citizenship=citizenship,
    )
    if not expected_docs:
        expected_docs = load_hr_expected_documents()
    control_tasks = await list_document_control_tasks(db, tenant_id=tid, employee_id=eid)
    control_tasks_out = [
        {
            "document_code": str(x.document_code or ""),
            "owner": x.owner,
            "next_action": x.next_action,
            "next_due_date": x.next_due_date.isoformat() if x.next_due_date else None,
            "comment": x.comment,
            "status": x.status,
            "updated_at": x.updated_at.isoformat() if x.updated_at else None,
        }
        for x in control_tasks
    ]

    eligibility_runtime = await resolve_workforce_eligibility_via_contract(
        db,
        context=WorkforceEligibilityContext(
            tenant_id=tid,
            employee_id=eid,
            candidate_id=str(emp.candidate_id) if emp.candidate_id else None,
            citizenship=(
                str(getattr(wel, "citizenship", "") or "").strip()
                or str((snap or {}).get("citizenship") or "").strip()
                or None
            ) if wel is not None else (str((snap or {}).get("citizenship") or "").strip() or None),
            work_country=(
                str(getattr(wel, "work_country", "") or "").strip()
                or str((snap or {}).get("work_country") or "").strip()
                or None
            ) if wel is not None else (str((snap or {}).get("work_country") or "").strip() or None),
            residence_status=(
                str(getattr(wel, "residence_status", "") or "").strip()
                or str((snap or {}).get("legal_status") or "").strip()
                or None
            ) if wel is not None else (str((snap or {}).get("legal_status") or "").strip() or None),
            position_category=(
                str(getattr(wel, "position_category", "") or "").strip()
                or str((snap or {}).get("position_category") or "").strip()
                or None
            ) if wel is not None else (str((snap or {}).get("position_category") or "").strip() or None),
            employment_type=str(getattr(latest, "contract_type", "") or "").strip() or None,
            stage="hr",
            client_id=str(emp.company_id) if emp.company_id else None,
            vacancy_id=vac_id,
        ),
    )

    # M5.2: legacy summary fields are compatibility projections from decision contract.
    dec_missing = len(list(eligibility_runtime.get("missing_documents") or []))
    dec_expiring = len(list(eligibility_runtime.get("soon_expiring_documents") or [])) + len(
        list(eligibility_runtime.get("expired_documents") or [])
    )
    operational_summary["compliance_status"] = str(eligibility_runtime.get("compliance_status") or comp_st)
    operational_summary["missing_documents_count"] = dec_missing
    operational_summary["expiring_documents_count"] = dec_expiring
    if str(eligibility_runtime.get("eligibility_status") or "") in {"blocked", "pending_documents", "expired_critical_documents"}:
        operational_summary["risk_level"] = "high"
    elif str(eligibility_runtime.get("eligibility_status") or "") in {"compliance_risk", "conditionally_eligible", "pending_verification"}:
        operational_summary["risk_level"] = "medium"
    else:
        operational_summary["risk_level"] = "low"

    return {
        "expected_documents": expected_docs,
        "document_control_tasks": control_tasks_out,
        "workforce_eligibility": eligibility_runtime,
        "employee_dossier": _build_employee_dossier(
            employee=emp,
            recruiter_summary=_recruiter_summary(snap),
            bundle=bundle,
            documents_missing=missing_items,
            documents_expiring=expiring_items,
            onboarding_overdue=overdue,
        ),
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
