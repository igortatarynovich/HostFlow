from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.models.workforce_onboarding_task import WorkforceOnboardingTask
from backend.app.models.workforce_payroll_profile import WorkforcePayrollProfile
from backend.app.models.workforce_zus_profile import WorkforceZusProfile
from backend.app.services.workforce_hr_core_profiles import ensure_workforce_hr_core_profiles, get_insurance_profile
from backend.app.services.workforce_work_eligibility import (
    ensure_work_eligibility_profile,
    get_work_eligibility_profile,
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
    return {
        "captured_at": now,
        "candidate_id": str(candidate.id),
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "company_id": candidate.company_id,
        "vacancy_id": candidate.vacancy_id,
        "stage": candidate.stage,
        "status": candidate.status,
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
            existing.candidate_snapshot = _candidate_snapshot(candidate)
            await db.flush()
        if seed_hr_bundle:
            await ensure_hr_profiles_bundle(db, tenant_id, existing.id)
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
        candidate_snapshot=snap,
        meta={"source": "recruitment_handoff"},
    )
    db.add(row)
    await db.flush()
    if seed_hr_bundle:
        await ensure_hr_profiles_bundle(db, tenant_id, row.id)
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
