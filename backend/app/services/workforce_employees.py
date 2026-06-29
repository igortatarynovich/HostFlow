from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.models.workforce_onboarding_task import WorkforceOnboardingTask
from backend.app.models.workforce_payroll_profile import WorkforcePayrollProfile
from backend.app.models.workforce_zus_profile import WorkforceZusProfile
from backend.app.services.workforce_hr_core_profiles import ensure_workforce_hr_core_profiles, get_insurance_profile
from backend.app.services.workforce_work_eligibility import (
    ensure_work_eligibility_profile,
    get_work_eligibility_profile,
    patch_work_eligibility_profile,
)
from backend.app.services.workforce_work_eligibility_payments import list_payment_requirements
from backend.app.models.workforce_absence import WorkforceAbsence
from backend.app.models.workforce_compliance_state import WorkforceComplianceState
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_document_context import WorkforceHrDocumentContext
from backend.app.models.workforce_insurance_profile import WorkforceInsuranceProfile
from backend.app.models.workforce_leave_request import WorkforceLeaveRequest
from backend.app.models.workforce_tax_profile import WorkforceTaxProfile

_logger = logging.getLogger(__name__)

# PR-5: Workforce employee for HR is materialized only via ``accept_handoff`` (internal_hr),
# not via candidate stage transitions. Do not reintroduce stage-driven paths — they duplicate
# handoff audit/ACL and risk double materialization.


def should_workforce_handoff_on_stage_change(
    old_stage: Optional[str], new_stage: Optional[str]
) -> bool:
    """Deprecated: always false. HR row creation is handoff-accept only."""
    return False


ALLOWED_STATUS = frozenset(
    {
        "onboarding",
        "active",
        "on_sick_leave",
        "on_vacation",
        "on_leave",
        "suspended",
        "contract_ending",
        "terminated",
    }
)

DEFAULT_ONBOARDING_TASK_TITLES: tuple[str, ...] = (
    "Sign employment contract",
    "Add to payroll system",
    "Hand off to dispatch",
    "Issue equipment",
    "Verify compliance documents",
    "Assign first route",
)


def _candidate_snapshot(candidate: Candidate) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    vacancy_ctx = _vacancy_context(candidate.vacancy)
    notes = {
        "candidate_note": candidate.note,
        "recruiter_notes": extra.get("recruiter_notes") or extra.get("internal_notes"),
        "handoff_notes": extra.get("handoff_notes") or extra.get("handoff_note"),
    }
    hr_identity = _hr_identity_fields(candidate=candidate, personal=personal, extra=extra, contacts=contacts)
    personal_augmented = dict(personal) if isinstance(personal, dict) else {}
    for key, value in hr_identity.items():
        if value in (None, ""):
            continue
        personal_augmented.setdefault(key, value)
    return {
        "captured_at": now,
        "candidate_id": str(candidate.id),
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "birth_date": hr_identity.get("birth_date"),
        "passport_number": hr_identity.get("passport_number"),
        "passport_series": hr_identity.get("passport_series"),
        "passport_issue_date": hr_identity.get("passport_issue_date"),
        "company_id": candidate.company_id,
        "vacancy_id": candidate.vacancy_id,
        "stage": candidate.stage,
        "status": candidate.status,
        "personal_data": personal_augmented,
        "contacts": contacts,
        "extra": extra,
        "hr_identity": hr_identity,
        "vacancy_context": vacancy_ctx,
        "citizenship": extra.get("citizenship") or personal.get("citizenship"),
        "work_country": extra.get("work_country") or personal.get("work_country"),
        "legal_status": extra.get("legal_status") or extra.get("residency_status") or personal.get("residency_status"),
        "position_category": (
            extra.get("position_category")
            or extra.get("profession")
            or extra.get("profession_category")
            or vacancy_ctx.get("position_category")
        ),
        "document_field_values": _document_related_field_values(extra, personal),
        "notes": {k: v for k, v in notes.items() if isinstance(v, str) and v.strip()},
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _vacancy_extra_dict(vacancy: Vacancy | None) -> dict[str, Any]:
    if not vacancy:
        return {}
    raw = getattr(vacancy, "extra", None)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _vacancy_context(vacancy: Vacancy | None) -> dict[str, Any]:
    if not vacancy:
        return {}
    vx = _vacancy_extra_dict(vacancy)
    out = {
        "vacancy_id": str(vacancy.id),
        "title": str(vacancy.title or "").strip() or None,
        "status": str(vacancy.status or "").strip() or None,
        "employment_type": str(vacancy.employment_type or "").strip() or None,
        "position_category": vx.get("position_category"),
    }
    return {k: v for k, v in out.items() if v is not None}


def _document_related_field_values(extra: dict[str, Any], personal: dict[str, Any]) -> dict[str, Any]:
    merged = {}
    merged.update(extra if isinstance(extra, dict) else {})
    merged.update(personal if isinstance(personal, dict) else {})
    keys = (
        "license_number",
        "license_categories",
        "license_valid_to",
        "driver_license_number",
        "driver_license_expiry",
        "driver_license_valid_to",
        "code95_number",
        "code95_expiry",
        "code_95_expiry",
        "tacho_card_number",
        "tacho_card_expiry",
        "tachograph_card_number",
        "tachograph_card_expiry",
        "tachograph_expiry",
        "medical_expiry",
        "medical_valid_to",
        "medical_exam_expiry",
        "pesel",
        "passport_number",
        "passport_series",
        "passport_issue_date",
        "passport_expiry",
        "passport_valid_to",
        "birth_date",
        "residence_card_number",
        "residence_card_valid_to",
        "work_permit_number",
        "work_permit_valid_to",
    )
    return {k: merged.get(k) for k in keys if merged.get(k) not in (None, "")}


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
            continue
        return value
    return None


def _hr_identity_fields(
    *,
    candidate: Candidate,
    personal: dict[str, Any],
    extra: dict[str, Any],
    contacts: dict[str, Any],
) -> dict[str, Any]:
    p = personal if isinstance(personal, dict) else {}
    e = extra if isinstance(extra, dict) else {}
    c = contacts if isinstance(contacts, dict) else {}

    address_val = _first_non_empty(
        p.get("address"),
        e.get("address"),
        getattr(candidate, "address", None),
    )
    if isinstance(address_val, dict):
        address_val = {k: v for k, v in address_val.items() if v not in (None, "")}

    return {
        "legal_name": _first_non_empty(
            p.get("legal_name"),
            p.get("full_name"),
            e.get("legal_name"),
            " ".join(x for x in [candidate.first_name, candidate.last_name] if x).strip(),
        ),
        "birth_date": _first_non_empty(
            p.get("birth_date"),
            e.get("birth_date"),
            getattr(candidate, "birth_date", None),
        ),
        "citizenship": _first_non_empty(
            p.get("citizenship"),
            e.get("citizenship"),
        ),
        "phone": _first_non_empty(
            p.get("phone"),
            c.get("phone"),
            candidate.phone,
        ),
        "email": _first_non_empty(
            p.get("email"),
            c.get("email"),
            candidate.email,
        ),
        "address": address_val,
        "pesel": _first_non_empty(
            p.get("pesel"),
            e.get("pesel"),
        ),
        "passport_number": _first_non_empty(
            p.get("passport_number"),
            e.get("passport_number"),
        ),
        "passport_series": _first_non_empty(
            p.get("passport_series"),
            e.get("passport_series"),
            e.get("passport_serie"),
        ),
        "passport_issue_date": _first_non_empty(
            p.get("passport_issue_date"),
            p.get("passport_issued_at"),
            e.get("passport_issue_date"),
            e.get("passport_issued_at"),
        ),
        "passport_expiry": _first_non_empty(
            p.get("passport_expiry"),
            p.get("passport_valid_to"),
            e.get("passport_expiry"),
            e.get("passport_valid_to"),
        ),
        "driver_license_number": _first_non_empty(
            p.get("driver_license_number"),
            p.get("license_number"),
            e.get("driver_license_number"),
            e.get("license_number"),
        ),
        "driver_license_expiry": _first_non_empty(
            p.get("driver_license_expiry"),
            p.get("driver_license_valid_to"),
            p.get("license_valid_to"),
            e.get("driver_license_expiry"),
            e.get("driver_license_valid_to"),
            e.get("license_valid_to"),
        ),
        "code95_expiry": _first_non_empty(
            p.get("code95_expiry"),
            p.get("code_95_expiry"),
            e.get("code95_expiry"),
            e.get("code_95_expiry"),
        ),
        "tachograph_expiry": _first_non_empty(
            p.get("tachograph_expiry"),
            p.get("tachograph_card_expiry"),
            p.get("tacho_card_expiry"),
            e.get("tachograph_expiry"),
            e.get("tachograph_card_expiry"),
            e.get("tacho_card_expiry"),
        ),
        "medical_expiry": _first_non_empty(
            p.get("medical_expiry"),
            p.get("medical_valid_to"),
            p.get("medical_exam_expiry"),
            e.get("medical_expiry"),
            e.get("medical_valid_to"),
            e.get("medical_exam_expiry"),
        ),
    }


def _handoff_meta_from_snapshot(
    candidate: Candidate,
    snap: dict[str, Any],
    *,
    internal_hr_handoff_id: str | None = None,
) -> dict[str, Any]:
    """PR17: recruitment context copied into employee.meta (modules stay separate)."""
    vacancy_ctx = snap.get("vacancy_context") if isinstance(snap.get("vacancy_context"), dict) else {}
    hr_identity = snap.get("hr_identity") if isinstance(snap.get("hr_identity"), dict) else {}
    meta: dict[str, Any] = {
        "source": "recruitment_handoff",
        "recruitment_transfer": {
            "candidate_id": str(candidate.id),
            "captured_at": snap.get("captured_at"),
            "citizenship": snap.get("citizenship") or hr_identity.get("citizenship"),
            "work_country": snap.get("work_country"),
            "position_category": snap.get("position_category") or vacancy_ctx.get("position_category"),
            "legal_status": snap.get("legal_status"),
            "vacancy_id": snap.get("vacancy_id"),
            "vacancy_title": vacancy_ctx.get("title"),
        },
    }
    if internal_hr_handoff_id:
        meta["internal_hr_handoff_id"] = internal_hr_handoff_id
    return meta


async def _seed_work_eligibility_from_candidate(
    db: AsyncSession, tenant_id: str, employee_id: str, candidate: Candidate
) -> None:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    vacancy_ctx = _vacancy_context(candidate.vacancy)
    patch: dict[str, Any] = {}

    def pick(*keys: str) -> Any:
        for key in keys:
            if key in personal and personal.get(key) not in (None, ""):
                return personal.get(key)
            if key in extra and extra.get(key) not in (None, ""):
                return extra.get(key)
        return None

    for target, sources in (
        ("citizenship", ("citizenship",)),
        ("residence_status", ("residency_status", "legal_status", "poland_stay_basis")),
        ("legal_stay_document_type", ("legal_stay_document_type", "residence_document_type")),
        ("work_country", ("work_country",)),
        ("position_category", ("position_category", "profession_category", "profession")),
        ("contract_type", ("contract_type",)),
    ):
        val = pick(*sources)
        if val not in (None, ""):
            patch[target] = val
    if "position_category" not in patch and vacancy_ctx.get("position_category"):
        patch["position_category"] = vacancy_ctx.get("position_category")
    if not patch:
        return
    await patch_work_eligibility_profile(db, tenant_id, employee_id, patch)


async def list_employees(
    db: AsyncSession,
    tenant_id: str,
    *,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[WorkforceEmployee]:
    stmt = select(WorkforceEmployee).where(WorkforceEmployee.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(WorkforceEmployee.status == status)
    stmt = stmt.order_by(WorkforceEmployee.created_at.desc()).offset(offset).limit(min(limit, 500))
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_hr_bundle(db: AsyncSession, tenant_id: str, employee_id: str) -> dict[str, Any]:
    """Nested HR satellites for one employee (empty lists / nulls when nothing stored yet)."""
    await ensure_workforce_hr_core_profiles(db, tenant_id, employee_id)
    await ensure_work_eligibility_profile(db, tenant_id, employee_id)
    await db.flush()

    emp_rows = (
        (
            await db.execute(
                select(WorkforceEmployment)
                .where(
                    WorkforceEmployment.tenant_id == tenant_id,
                    WorkforceEmployment.employee_id == employee_id,
                )
                .order_by(WorkforceEmployment.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    pay = (
        await db.execute(
            select(WorkforcePayrollProfile).where(
                WorkforcePayrollProfile.tenant_id == tenant_id,
                WorkforcePayrollProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()
    zus = (
        await db.execute(
            select(WorkforceZusProfile).where(
                WorkforceZusProfile.tenant_id == tenant_id,
                WorkforceZusProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()
    tasks = (
        (
            await db.execute(
                select(WorkforceOnboardingTask)
                .where(
                    WorkforceOnboardingTask.tenant_id == tenant_id,
                    WorkforceOnboardingTask.employee_id == employee_id,
                )
                .order_by(WorkforceOnboardingTask.sort_order.asc(), WorkforceOnboardingTask.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    absences = (
        (
            await db.execute(
                select(WorkforceAbsence)
                .where(
                    WorkforceAbsence.tenant_id == tenant_id,
                    WorkforceAbsence.employee_id == employee_id,
                )
                .order_by(WorkforceAbsence.start_date.desc(), WorkforceAbsence.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    leaves = (
        (
            await db.execute(
                select(WorkforceLeaveRequest)
                .where(
                    WorkforceLeaveRequest.tenant_id == tenant_id,
                    WorkforceLeaveRequest.employee_id == employee_id,
                )
                .order_by(WorkforceLeaveRequest.start_date.desc(), WorkforceLeaveRequest.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    tax = (
        await db.execute(
            select(WorkforceTaxProfile).where(
                WorkforceTaxProfile.tenant_id == tenant_id,
                WorkforceTaxProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()
    ins = (
        await db.execute(
            select(WorkforceInsuranceProfile).where(
                WorkforceInsuranceProfile.tenant_id == tenant_id,
                WorkforceInsuranceProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()
    comp = (
        await db.execute(
            select(WorkforceComplianceState).where(
                WorkforceComplianceState.tenant_id == tenant_id,
                WorkforceComplianceState.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()

    ctx_total = int(
        (
            await db.execute(
                select(func.count())
                .select_from(WorkforceHrDocumentContext)
                .where(
                    WorkforceHrDocumentContext.tenant_id == tenant_id,
                    WorkforceHrDocumentContext.employee_id == employee_id,
                )
            )
        ).scalar_one()
        or 0
    )
    grp_rows = (
        await db.execute(
            select(WorkforceHrDocumentContext.context_type, func.count())
            .where(
                WorkforceHrDocumentContext.tenant_id == tenant_id,
                WorkforceHrDocumentContext.employee_id == employee_id,
            )
            .group_by(WorkforceHrDocumentContext.context_type)
        )
    ).all()
    by_context_type: dict[str, int] = {}
    for ct, c in grp_rows:
        key = str(ct or "").strip() or "(empty)"
        by_context_type[key] = int(c or 0)
    ctx_items = list(
        (
            await db.execute(
                select(WorkforceHrDocumentContext)
                .where(
                    WorkforceHrDocumentContext.tenant_id == tenant_id,
                    WorkforceHrDocumentContext.employee_id == employee_id,
                )
                .order_by(WorkforceHrDocumentContext.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )

    wel = await get_work_eligibility_profile(db, tenant_id, employee_id)
    pay_reqs = await list_payment_requirements(db, tenant_id, employee_id)

    return {
        "employments": emp_rows,
        "payroll_profile": pay,
        "zus_profile": zus,
        "onboarding_tasks": tasks,
        "absences": absences,
        "leave_requests": leaves,
        "tax_profile": tax,
        "insurance_profile": ins,
        "compliance_state": comp,
        "work_eligibility_profile": wel,
        "work_eligibility_payment_requirements": pay_reqs,
        "hr_document_context_summary": {
            "total": ctx_total,
            "by_context_type": by_context_type,
            "items": ctx_items,
        },
    }


async def get_employee(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> Optional[WorkforceEmployee]:
    res = await db.execute(
        select(WorkforceEmployee).where(
            WorkforceEmployee.id == employee_id,
            WorkforceEmployee.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


async def ensure_hr_profiles_bundle(db: AsyncSession, tenant_id: str, employee_id: str) -> None:
    """Idempotent: create MVP HR profile rows + onboarding checklist when missing."""
    emp_cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceEmployment)
            .where(
                WorkforceEmployment.tenant_id == tenant_id,
                WorkforceEmployment.employee_id == employee_id,
            )
        )
    ).scalar_one()
    if not int(emp_cnt or 0):
        db.add(
            WorkforceEmployment(
                id=str(uuid4()),
                tenant_id=tenant_id,
                employee_id=employee_id,
                contract_type="unknown",
                meta={"source": "auto_bundle"},
            )
        )

    pay_cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforcePayrollProfile)
            .where(
                WorkforcePayrollProfile.tenant_id == tenant_id,
                WorkforcePayrollProfile.employee_id == employee_id,
            )
        )
    ).scalar_one()
    if not int(pay_cnt or 0):
        db.add(
            WorkforcePayrollProfile(
                id=str(uuid4()),
                tenant_id=tenant_id,
                employee_id=employee_id,
                pay_type="mixed",
                payroll_status="missing_data",
                meta={"source": "auto_bundle"},
            )
        )

    zus_cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceZusProfile)
            .where(
                WorkforceZusProfile.tenant_id == tenant_id,
                WorkforceZusProfile.employee_id == employee_id,
            )
        )
    ).scalar_one()
    if not int(zus_cnt or 0):
        db.add(
            WorkforceZusProfile(
                id=str(uuid4()),
                tenant_id=tenant_id,
                employee_id=employee_id,
                registration_status="not_submitted",
                meta={"source": "auto_bundle"},
            )
        )

    task_cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceOnboardingTask)
            .where(
                WorkforceOnboardingTask.tenant_id == tenant_id,
                WorkforceOnboardingTask.employee_id == employee_id,
            )
        )
    ).scalar_one()
    if not int(task_cnt or 0):
        for idx, title in enumerate(DEFAULT_ONBOARDING_TASK_TITLES):
            db.add(
                WorkforceOnboardingTask(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    employee_id=employee_id,
                    title=title,
                    sort_order=idx,
                    status="open",
                    meta={"source": "auto_bundle"},
                )
            )

    await ensure_workforce_hr_core_profiles(db, tenant_id, employee_id)
    await ensure_work_eligibility_profile(db, tenant_id, employee_id)
    await db.flush()


async def create_employee(
    db: AsyncSession,
    tenant_id: str,
    *,
    display_name: str,
    status: str = "onboarding",
    own_company_id: Optional[str] = None,
    company_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
    recruiter_user_id: Optional[str] = None,
    candidate_snapshot: Optional[dict[str, Any]] = None,
    hire_date: Optional[date] = None,
    probation_end: Optional[date] = None,
    notes: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    initial_insurance_zus_registration_type: Optional[str] = None,
    initial_insurance_status: Optional[str] = None,
    initial_eligibility_status: Optional[str] = None,
) -> WorkforceEmployee:
    st = status if status in ALLOWED_STATUS else "onboarding"
    row = WorkforceEmployee(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        candidate_id=candidate_id,
        company_id=company_id,
        vacancy_id=vacancy_id,
        recruiter_user_id=recruiter_user_id,
        display_name=display_name.strip(),
        status=st,
        hire_date=hire_date,
        probation_end=probation_end,
        notes=notes,
        candidate_snapshot=candidate_snapshot,
        meta=meta,
    )
    db.add(row)
    await db.flush()
    await ensure_hr_profiles_bundle(db, tenant_id, row.id)
    if (initial_insurance_zus_registration_type or "").strip():
        ins = await get_insurance_profile(db, tenant_id, row.id)
        if ins:
            ins.zus_registration_type = str(initial_insurance_zus_registration_type).strip()[:64]
            ins.status = str(initial_insurance_status or "pending_registration").strip()[:32]
            await db.flush()
    if (initial_eligibility_status or "").strip():
        wel = await get_work_eligibility_profile(db, tenant_id, row.id)
        if wel:
            wel.eligibility_status = str(initial_eligibility_status).strip()[:32]
            await db.flush()
    from backend.app.services.workforce_zus_task_autocreate import sync_auto_tasks_after_employee_created

    await sync_auto_tasks_after_employee_created(db, tenant_id, row.id)
    return row


async def find_employee_by_candidate(
    db: AsyncSession, tenant_id: str, candidate_id: str
) -> Optional[WorkforceEmployee]:
    res = await db.execute(
        select(WorkforceEmployee).where(
            WorkforceEmployee.tenant_id == tenant_id,
            WorkforceEmployee.candidate_id == candidate_id,
        )
    )
    return res.scalar_one_or_none()


async def handoff_from_candidate(
    db: AsyncSession,
    tenant_id: str,
    candidate: Candidate,
    *,
    hire_date: Optional[date],
    actor_user_id: str,
    seed_hr_bundle: bool = True,
) -> WorkforceEmployee:
    existing = await find_employee_by_candidate(db, tenant_id, str(candidate.id))
    if existing:
        status_l = str(getattr(existing, "status", "") or "").strip().lower()
        if status_l in ("returned_to_recruitment", "returned"):
            now = _now()
            existing.status = "onboarding"
            existing.handoff_at = now
            existing.handoff_by_user_id = actor_user_id
            snap = _candidate_snapshot(candidate)
            existing.candidate_snapshot = snap
            md = dict(existing.meta or {})
            md.update(_handoff_meta_from_snapshot(candidate, snap))
            existing.meta = md
            if not (existing.notes or "").strip():
                existing.notes = str(candidate.note or "").strip() or None
            await db.flush()
        if seed_hr_bundle:
            await ensure_hr_profiles_bundle(db, tenant_id, existing.id)
            await _seed_work_eligibility_from_candidate(db, tenant_id, existing.id, candidate)
            from backend.app.services.workforce_zus_task_autocreate import sync_auto_tasks_after_employee_created

            await sync_auto_tasks_after_employee_created(db, tenant_id, existing.id)
        return existing

    parts = [candidate.first_name or "", candidate.last_name or ""]
    display_name = " ".join(p for p in parts if p).strip() or (candidate.email or "Employee")
    now = _now()
    snap = _candidate_snapshot(candidate)
    row = WorkforceEmployee(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=candidate.own_company_id,
        candidate_id=str(candidate.id),
        company_id=candidate.company_id,
        vacancy_id=str(candidate.vacancy_id) if candidate.vacancy_id else None,
        recruiter_user_id=str(candidate.recruiter_id) if candidate.recruiter_id else None,
        display_name=display_name,
        status="onboarding",
        hire_date=hire_date,
        handoff_at=now,
        handoff_by_user_id=actor_user_id,
        notes=str(candidate.note or "").strip() or None,
        candidate_snapshot=snap,
        meta=_handoff_meta_from_snapshot(candidate, snap),
    )
    db.add(row)
    await db.flush()
    if seed_hr_bundle:
        await ensure_hr_profiles_bundle(db, tenant_id, row.id)
        await _seed_work_eligibility_from_candidate(db, tenant_id, row.id, candidate)
        from backend.app.services.workforce_zus_task_autocreate import sync_auto_tasks_after_employee_created

        await sync_auto_tasks_after_employee_created(db, tenant_id, row.id)
    return row


async def delete_employee_for_return_to_recruitment(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> None:
    """Remove workforce row so recruitment regains operational ownership (§6.7 return-to-recruitment)."""
    emp = await get_employee(db, tenant_id, employee_id)
    if not emp:
        return
    await db.delete(emp)
    await db.flush()


async def stamp_candidate_workforce_termination(
    db: AsyncSession,
    tenant_id: str,
    *,
    candidate_id: str,
    termination_date: Optional[date],
    employee_status: str,
    actor_user_id: str,
) -> None:
    """Merge termination facts into ``candidate.extra["workforce_termination"]`` (does not change stage)."""
    res = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
        )
    )
    cand = res.scalar_one_or_none()
    if not cand:
        return
    try:
        extra = json.loads(cand.extra or "{}")
    except Exception:
        extra = {}
    if not isinstance(extra, dict):
        extra = {}
    extra["workforce_termination"] = {
        "employee_status": employee_status,
        "termination_date": termination_date.isoformat() if termination_date else None,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "recorded_by_user_id": actor_user_id,
    }
    try:
        await db.execute(
            update(Candidate)
            .where(Candidate.id == candidate_id, Candidate.tenant_id == tenant_id)
            .values(
                extra=json.dumps(extra, ensure_ascii=False),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
    except Exception:
        _logger.exception(
            "stamp_candidate_workforce_termination failed tenant=%s candidate=%s",
            tenant_id,
            candidate_id,
        )
        raise
