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
from backend.app.models.workforce_absence import WorkforceAbsence
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_leave_request import WorkforceLeaveRequest

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
    return {
        "employments": emp_rows,
        "payroll_profile": pay,
        "zus_profile": zus,
        "onboarding_tasks": tasks,
        "absences": absences,
        "leave_requests": leaves,
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
) -> WorkforceEmployee:
    existing = await find_employee_by_candidate(db, tenant_id, str(candidate.id))
    if existing:
        await ensure_hr_profiles_bundle(db, tenant_id, existing.id)
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
    await ensure_hr_profiles_bundle(db, tenant_id, row.id)
    return row


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
