from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.api.v1.candidate_documents import CandDoc
from backend.app.api.v1.candidates.service import get_candidate
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.documents import crud as documents_crud
from backend.app.schemas.workforce_hr import (
    AbsenceCreate,
    AbsencePatch,
    EmploymentCreate,
    EmploymentPatch,
    LeaveRequestCreate,
    LeaveRequestPatch,
    OnboardingTaskPatch,
    PayrollProfilePatch,
    ZusProfilePatch,
)
from backend.app.services import workforce_hr_satellites as wh_sat
from backend.app.services import workforce_employees as we_svc
from backend.app.services.audit import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workforce", tags=["workforce"])

# HR workspace: list/detail/create/update (not visible to pure recruitment roles)
HR_WORKSPACE_ROLES = (Role.hr_officer, Role.administrator, Role.supervisor)
# Recruitment / managers with candidate access (HR officers use list/create in workspace, not this)
HANDOFF_ROLES = (
    Role.recruiter,
    Role.compliance_officer,
    Role.administrator,
    Role.supervisor,
    Role.client_manager,
    Role.client_processor,
)


class EmployeeOut(BaseModel):
    id: str
    tenant_id: str
    own_company_id: Optional[str] = None
    candidate_id: Optional[str] = None
    company_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    recruiter_user_id: Optional[str] = None
    display_name: str
    status: str
    hire_date: Optional[date] = None
    probation_end: Optional[date] = None
    termination_date: Optional[date] = None
    handoff_at: Optional[str] = None
    handoff_by_user_id: Optional[str] = None
    notes: Optional[str] = None
    candidate_snapshot: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: Any) -> "EmployeeOut":
        return cls(
            id=row.id,
            tenant_id=row.tenant_id,
            own_company_id=row.own_company_id,
            candidate_id=row.candidate_id,
            company_id=row.company_id,
            vacancy_id=row.vacancy_id,
            recruiter_user_id=row.recruiter_user_id,
            display_name=row.display_name,
            status=row.status,
            hire_date=row.hire_date,
            probation_end=row.probation_end,
            termination_date=row.termination_date,
            handoff_at=row.handoff_at.isoformat() if row.handoff_at else None,
            handoff_by_user_id=row.handoff_by_user_id,
            notes=row.notes,
            candidate_snapshot=row.candidate_snapshot,
            meta=row.meta,
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )


class EmployeeCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=512)
    status: str = Field(default="onboarding", max_length=32)
    own_company_id: Optional[str] = None
    company_id: Optional[str] = None
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    recruiter_user_id: Optional[str] = None
    candidate_snapshot: Optional[dict[str, Any]] = None
    hire_date: Optional[date] = None
    probation_end: Optional[date] = None
    notes: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class EmployeePatch(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=512)
    status: Optional[str] = Field(default=None, max_length=32)
    own_company_id: Optional[str] = None
    company_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    recruiter_user_id: Optional[str] = None
    candidate_snapshot: Optional[dict[str, Any]] = None
    hire_date: Optional[date] = None
    probation_end: Optional[date] = None
    termination_date: Optional[date] = None
    notes: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class HandoffIn(BaseModel):
    hire_date: Optional[date] = None


def _dec_str(v: Optional[Decimal]) -> Optional[str]:
    if v is None:
        return None
    return format(v, "f")


class EmploymentOut(BaseModel):
    id: str
    employee_id: str
    contract_type: str
    rate_model: Optional[dict[str, Any]] = None
    schedule: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    conditions_text: Optional[str] = None
    vacancy_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class PayrollProfileOut(BaseModel):
    id: str
    employee_id: str
    pay_type: str
    base_rate: Optional[str] = None
    currency: Optional[str] = None
    calculation_system: Optional[str] = None
    pay_day_note: Optional[str] = None
    bank_account: Optional[str] = None
    tax_status: Optional[str] = None
    pit_declarations: Optional[dict[str, Any]] = None
    allowances: Optional[dict[str, Any]] = None
    deductions: Optional[dict[str, Any]] = None
    payroll_status: str
    external_refs: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class ZusProfileOut(BaseModel):
    id: str
    employee_id: str
    registration_status: str
    submitted_at: Optional[date] = None
    employment_basis: Optional[str] = None
    responsible_party: Optional[str] = None
    insurance_coverage: Optional[dict[str, Any]] = None
    forms: Optional[list[Any]] = None
    meta: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class OnboardingTaskOut(BaseModel):
    id: str
    employee_id: str
    title: str
    sort_order: int
    status: str
    due_at: Optional[str] = None
    completed_at: Optional[str] = None
    assignee_user_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class AbsenceOut(BaseModel):
    id: str
    employee_id: str
    absence_type: str
    start_date: date
    end_date: Optional[date] = None
    source: str
    status: str
    payer: Optional[str] = None
    payroll_impact: Optional[str] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class LeaveRequestOut(BaseModel):
    id: str
    employee_id: str
    leave_type: str
    start_date: date
    end_date: date
    status: str
    year_entitlement_days: Optional[str] = None
    used_days_before: Optional[str] = None
    conflict_flags: Optional[dict[str, Any]] = None
    approver_user_id: Optional[str] = None
    decided_at: Optional[str] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class HrBundleOut(BaseModel):
    employments: List[EmploymentOut]
    payroll_profile: Optional[PayrollProfileOut] = None
    zus_profile: Optional[ZusProfileOut] = None
    onboarding_tasks: List[OnboardingTaskOut]
    absences: List[AbsenceOut]
    leave_requests: List[LeaveRequestOut]


def _employment_out(row: Any) -> EmploymentOut:
    return EmploymentOut(
        id=row.id,
        employee_id=row.employee_id,
        contract_type=row.contract_type,
        rate_model=row.rate_model,
        schedule=row.schedule,
        start_date=row.start_date,
        end_date=row.end_date,
        conditions_text=row.conditions_text,
        vacancy_id=row.vacancy_id,
        meta=row.meta,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _payroll_out(row: Any) -> PayrollProfileOut:
    return PayrollProfileOut(
        id=row.id,
        employee_id=row.employee_id,
        pay_type=row.pay_type,
        base_rate=_dec_str(row.base_rate),
        currency=row.currency,
        calculation_system=row.calculation_system,
        pay_day_note=row.pay_day_note,
        bank_account=row.bank_account,
        tax_status=row.tax_status,
        pit_declarations=row.pit_declarations,
        allowances=row.allowances,
        deductions=row.deductions,
        payroll_status=row.payroll_status,
        external_refs=row.external_refs,
        meta=row.meta,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _zus_out(row: Any) -> ZusProfileOut:
    return ZusProfileOut(
        id=row.id,
        employee_id=row.employee_id,
        registration_status=row.registration_status,
        submitted_at=row.submitted_at,
        employment_basis=row.employment_basis,
        responsible_party=row.responsible_party,
        insurance_coverage=row.insurance_coverage,
        forms=row.forms,
        meta=row.meta,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _task_out(row: Any) -> OnboardingTaskOut:
    return OnboardingTaskOut(
        id=row.id,
        employee_id=row.employee_id,
        title=row.title,
        sort_order=int(row.sort_order or 0),
        status=row.status,
        due_at=row.due_at.isoformat() if row.due_at else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        assignee_user_id=row.assignee_user_id,
        meta=row.meta,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _absence_out(row: Any) -> AbsenceOut:
    return AbsenceOut(
        id=row.id,
        employee_id=row.employee_id,
        absence_type=row.absence_type,
        start_date=row.start_date,
        end_date=row.end_date,
        source=row.source,
        status=row.status,
        payer=row.payer,
        payroll_impact=row.payroll_impact,
        comment=row.comment,
        meta=row.meta,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _leave_out(row: Any) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=row.id,
        employee_id=row.employee_id,
        leave_type=row.leave_type,
        start_date=row.start_date,
        end_date=row.end_date,
        status=row.status,
        year_entitlement_days=_dec_str(row.year_entitlement_days),
        used_days_before=_dec_str(row.used_days_before),
        conflict_flags=row.conflict_flags,
        approver_user_id=row.approver_user_id,
        decided_at=row.decided_at.isoformat() if row.decided_at else None,
        comment=row.comment,
        meta=row.meta,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


@router.get(
    "/employees",
    response_model=List[EmployeeOut],
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def list_employees(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> List[EmployeeOut]:
    db, tid = db_tenant
    tenant_id = str(tid)
    rows = await we_svc.list_employees(db, tenant_id, status=status, limit=limit, offset=offset)
    return [EmployeeOut.from_orm_row(r) for r in rows]


@router.get(
    "/employees/{employee_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> EmployeeOut:
    db, tid = db_tenant
    row = await we_svc.get_employee(db, str(tid), employee_id)
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeOut.from_orm_row(row)


@router.get(
    "/employees/{employee_id}/hr-bundle",
    response_model=HrBundleOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee_hr_bundle(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> HrBundleOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    row = await we_svc.get_employee(db, tenant_id, employee_id)
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    bundle = await we_svc.get_hr_bundle(db, tenant_id, employee_id)
    return HrBundleOut(
        employments=[_employment_out(r) for r in bundle["employments"]],
        payroll_profile=_payroll_out(bundle["payroll_profile"]) if bundle["payroll_profile"] else None,
        zus_profile=_zus_out(bundle["zus_profile"]) if bundle["zus_profile"] else None,
        onboarding_tasks=[_task_out(r) for r in bundle["onboarding_tasks"]],
        absences=[_absence_out(r) for r in bundle["absences"]],
        leave_requests=[_leave_out(r) for r in bundle["leave_requests"]],
    )


@router.get(
    "/employees/{employee_id}/documents",
    response_model=List[CandDoc],
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def list_employee_documents_via_candidate_link(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> List[CandDoc]:
    """
    Documents for the recruitment candidate linked to this employee (same data plane as dossier).
    HR officers cannot call `/candidates/.../documents` directly — this endpoint scopes access via workforce row.
    """
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    cid = (emp.candidate_id or "").strip()
    if not cid:
        return []
    rows = await documents_crud.list_candidate_documents(
        db,
        tenant_id,
        cid,
        active_own_company_id=own_company_id,
    )
    return [CandDoc.from_document(r) for r in rows]


@router.post(
    "/employees",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def create_employee_endpoint(
    payload: EmployeeCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> EmployeeOut:
    db, tid = db_tenant
    row = await we_svc.create_employee(
        db,
        str(tid),
        display_name=payload.display_name,
        status=payload.status,
        own_company_id=payload.own_company_id,
        company_id=payload.company_id,
        candidate_id=payload.candidate_id,
        vacancy_id=payload.vacancy_id,
        recruiter_user_id=payload.recruiter_user_id,
        candidate_snapshot=payload.candidate_snapshot,
        hire_date=payload.hire_date,
        probation_end=payload.probation_end,
        notes=payload.notes,
        meta=payload.meta,
    )
    await db.commit()
    await db.refresh(row)
    return EmployeeOut.from_orm_row(row)


@router.patch(
    "/employees/{employee_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_employee(
    employee_id: str,
    payload: EmployeePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmployeeOut:
    db, tid = db_tenant
    data = payload.model_dump(exclude_unset=True)
    row = await we_svc.get_employee(db, str(tid), employee_id)
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    prev_status = row.status
    prev_term = row.termination_date
    candidate_link = (row.candidate_id or "").strip() or None
    for k, v in data.items():
        setattr(row, k, v)
    if hasattr(row, "updated_at"):
        from datetime import datetime, timezone

        row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)

    touched_term = "termination_date" in data or "status" in data
    became_terminated = (row.status or "").lower() == "terminated" and (prev_status or "").lower() != "terminated"
    term_date_changed = "termination_date" in data and prev_term != row.termination_date
    term_signal = bool(candidate_link and touched_term and (became_terminated or term_date_changed))
    if term_signal:
        try:
            await we_svc.stamp_candidate_workforce_termination(
                db,
                str(tid),
                candidate_id=candidate_link,
                termination_date=row.termination_date,
                employee_status=str(row.status or ""),
                actor_user_id=str(current_user.sub),
            )
            await db.commit()
        except Exception:
            logger.exception(
                "stamp_candidate_workforce_termination failed employee=%s candidate=%s",
                employee_id,
                candidate_link,
            )
            try:
                await db.rollback()
            except Exception:
                pass

    return EmployeeOut.from_orm_row(row)


@router.post(
    "/employees/from-candidate/{candidate_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_roles(*HANDOFF_ROLES))],
)
async def handoff_employee_from_candidate(
    candidate_id: str,
    body: HandoffIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmployeeOut:
    """
    Create a workforce employee from a candidate (recruitment handoff to HR data model).
    Idempotent: returns existing row if already linked to this candidate.
    """
    db, tid = db_tenant
    tenant_id = str(tid)
    await ensure_candidate_access(db, tenant_id, candidate_id, current_user)
    c = await get_candidate(db, tenant_id, candidate_id)
    row = await we_svc.handoff_from_candidate(
        db,
        tenant_id,
        c,
        hire_date=body.hire_date,
        actor_user_id=current_user.sub,
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.handoff_from_candidate",
        actor_id=current_user.sub,
        target_type="workforce_employee",
        target_id=row.id,
        payload={"candidate_id": str(candidate_id)},
    )
    await db.commit()
    await db.refresh(row)
    return EmployeeOut.from_orm_row(row)


@router.patch(
    "/employees/{employee_id}/payroll-profile",
    response_model=PayrollProfileOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_payroll_profile_endpoint(
    employee_id: str,
    payload: PayrollProfilePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> PayrollProfileOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_payroll_profile(db, tenant_id, employee_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Employee or payroll profile not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.payroll_profile_patch",
        actor_id=current_user.sub,
        target_type="workforce_payroll_profile",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return _payroll_out(row)


@router.patch(
    "/employees/{employee_id}/zus-profile",
    response_model=ZusProfileOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_zus_profile_endpoint(
    employee_id: str,
    payload: ZusProfilePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ZusProfileOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_zus_profile(db, tenant_id, employee_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Employee or ZUS profile not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.zus_profile_patch",
        actor_id=current_user.sub,
        target_type="workforce_zus_profile",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return _zus_out(row)


@router.post(
    "/employees/{employee_id}/employments",
    response_model=EmploymentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def create_employment_endpoint(
    employee_id: str,
    payload: EmploymentCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmploymentOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    row = await wh_sat.create_employment(db, tenant_id, employee_id, payload.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.employment_create",
        actor_id=current_user.sub,
        target_type="workforce_employment",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return _employment_out(row)


@router.patch(
    "/employments/{employment_id}",
    response_model=EmploymentOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_employment_endpoint(
    employment_id: str,
    payload: EmploymentPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmploymentOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_employment(db, tenant_id, employment_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Employment not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.employment_patch",
        actor_id=current_user.sub,
        target_type="workforce_employment",
        target_id=row.id,
        payload={},
    )
    await db.commit()
    await db.refresh(row)
    return _employment_out(row)


@router.patch(
    "/onboarding-tasks/{task_id}",
    response_model=OnboardingTaskOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_onboarding_task_endpoint(
    task_id: str,
    payload: OnboardingTaskPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> OnboardingTaskOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_onboarding_task(db, tenant_id, task_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Onboarding task not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.onboarding_task_patch",
        actor_id=current_user.sub,
        target_type="workforce_onboarding_task",
        target_id=row.id,
        payload={},
    )
    await db.commit()
    await db.refresh(row)
    return _task_out(row)


@router.post(
    "/employees/{employee_id}/absences",
    response_model=AbsenceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def create_absence_endpoint(
    employee_id: str,
    payload: AbsenceCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> AbsenceOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    row = await wh_sat.create_absence(db, tenant_id, employee_id, payload.model_dump())
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.absence_create",
        actor_id=current_user.sub,
        target_type="workforce_absence",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return _absence_out(row)


@router.patch(
    "/absences/{absence_id}",
    response_model=AbsenceOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_absence_endpoint(
    absence_id: str,
    payload: AbsencePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> AbsenceOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_absence(db, tenant_id, absence_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Absence not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.absence_patch",
        actor_id=current_user.sub,
        target_type="workforce_absence",
        target_id=row.id,
        payload={},
    )
    await db.commit()
    await db.refresh(row)
    return _absence_out(row)


@router.post(
    "/employees/{employee_id}/leave-requests",
    response_model=LeaveRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def create_leave_request_endpoint(
    employee_id: str,
    payload: LeaveRequestCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> LeaveRequestOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    row = await wh_sat.create_leave_request(db, tenant_id, employee_id, payload.model_dump())
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.leave_request_create",
        actor_id=current_user.sub,
        target_type="workforce_leave_request",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return _leave_out(row)


@router.patch(
    "/leave-requests/{leave_id}",
    response_model=LeaveRequestOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_leave_request_endpoint(
    leave_id: str,
    payload: LeaveRequestPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> LeaveRequestOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_leave_request(
        db, tenant_id, leave_id, data, actor_user_id=current_user.sub
    )
    if not row:
        raise HTTPException(status_code=404, detail="Leave request not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.leave_request_patch",
        actor_id=current_user.sub,
        target_type="workforce_leave_request",
        target_id=row.id,
        payload={},
    )
    await db.commit()
    await db.refresh(row)
    return _leave_out(row)
