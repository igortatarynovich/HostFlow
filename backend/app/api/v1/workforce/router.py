from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.api.v1.candidate_documents import CandDoc
from backend.app.modules.documents.document_open_service import (
    build_workforce_cand_doc,
    stream_workforce_employee_document_file,
)
from backend.app.api.v1.candidates.service import get_candidate
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.documents import crud as documents_crud
from backend.app.models.workforce_leave_request import WorkforceLeaveRequest
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.schemas.workforce_hr import (
    AbsenceCreate,
    AbsencePatch,
    ComplianceStatePatch,
    EmploymentCreate,
    EmploymentPatch,
    InsuranceProfilePatch,
    LeaveRequestCreate,
    LeaveRequestPatch,
    OnboardingTaskPatch,
    PayrollProfilePatch,
    TaxProfilePatch,
    WorkEligibilityPaymentRequirementPatch,
    WorkEligibilityProfilePatch,
    HrDocumentControlTaskPatch,
    ZusProfilePatch,
)
from backend.app.schemas.workforce_hr_core import (
    HrDocumentCorrectionIn,
    HrAdditionalDocumentRequestIn,
    HrDocumentRequirementWaiverIn,
    HrDocumentRejectIn,
    HrDocumentReviewedFieldsIn,
    HrReviewChecklistPatchIn,
    HrReviewDocumentRowOut,
    HrReviewNoteIn,
    HrReviewPanelOut,
    HrReviewReasonIn,
    HrVerifiedFieldOut,
    HrVerifiedFieldOverrideIn,
    ContractDraftPreviewIn,
    ContractDraftPreviewOut,
    TrustedIdentityPrepStatusOut,
    WorkforceComplianceStateOut,
    WorkforceHrDocumentContextOut,
    WorkforceHrDocumentContextSummaryOut,
    WorkforceInsuranceProfileOut,
    WorkforceTaxProfileOut,
    WorkforceWorkEligibilityPaymentRequirementOut,
    WorkforceWorkEligibilityProfileOut,
    WorkEligibilityJourneyOut,
)
from backend.app.services import hr_document_verification as doc_verify_svc
from backend.app.services import hr_verified_fields as vf_svc
from backend.app.services import workforce_hr_review as hr_review_svc
from backend.app.services import workforce_hr_satellites as wh_sat
from backend.app.services import workforce_hr_operational_context as hr_ctx_svc
from backend.app.services import workforce_employees as we_svc
from backend.app.services import workforce_directory as wf_directory
from backend.app.services import workforce_operational_profile as wf_op
from backend.app.services import hr_document_control_tasks as doc_task_svc
from backend.app.services import workforce_work_eligibility as wel_svc
from backend.app.services import workforce_work_eligibility_payments as wel_pay_svc
from backend.app.services import hr_lifecycle_ledger as ledger_svc
from backend.app.services.workforce_work_eligibility_journey import build_work_eligibility_journey
from backend.app.services.workforce_zus_task_autocreate import ensure_zus_registration_task
from backend.app.services.workforce_action_policy import (
    WorkforceActionBlockedError,
    assert_operation_allowed,
)
from backend.app.services.audit import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workforce", tags=["workforce"])

# HR workspace: list/detail/create/update (not visible to pure recruitment roles)
HR_WORKSPACE_ROLES = (Role.hr_officer, Role.administrator, Role.supervisor)
# HR-only document review lane (recruitment/supervisor must not mutate HR checks)
HR_DOCUMENT_REVIEW_ROLES = (Role.hr_officer, Role.administrator)
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
    pipeline_stage: Optional[str] = Field(default=None, max_length=64)
    initial_insurance_zus_registration_type: Optional[str] = Field(default=None, max_length=64)
    initial_insurance_status: Optional[str] = Field(default=None, max_length=32)
    initial_eligibility_status: Optional[str] = Field(default=None, max_length=32)


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


class EmployeeDirectoryRowOut(BaseModel):
    employee_id: str
    full_name: str
    status: str
    employer: Optional[str] = None
    client: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    assigned_hr: Optional[str] = None
    assigned_hr_user_id: Optional[str] = None
    handoff_id: Optional[str] = None
    candidate_id: Optional[str] = None
    compliance_status: str
    missing_documents_count: int
    expiring_documents_count: int
    risk_level: str
    hr_review_status: Optional[str] = None
    documents_verified_count: Optional[int] = None
    documents_total_count: Optional[int] = None


class EmployeeDirectoryPageOut(BaseModel):
    items: List[EmployeeDirectoryRowOut]
    total: int


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
    lifecycle_status: str
    employer_name: Optional[str] = None
    rate_model: Optional[dict[str, Any]] = None
    schedule: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    probation_end: Optional[date] = None
    signed_at: Optional[date] = None
    latest_annex_ref: Optional[str] = None
    expiry_date: Optional[date] = None
    next_action: Optional[str] = None
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
    tax_profile: Optional[WorkforceTaxProfileOut] = None
    insurance_profile: Optional[WorkforceInsuranceProfileOut] = None
    work_eligibility_profile: Optional[WorkforceWorkEligibilityProfileOut] = None
    work_eligibility_payment_requirements: List[WorkforceWorkEligibilityPaymentRequirementOut] = Field(
        default_factory=list
    )
    compliance_state: Optional[WorkforceComplianceStateOut] = None
    hr_document_context_summary: WorkforceHrDocumentContextSummaryOut = Field(
        default_factory=WorkforceHrDocumentContextSummaryOut
    )


class OperationalSummaryOut(BaseModel):
    employee_status: str
    full_name: str
    employer: Optional[str] = None
    client: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    probation_end: Optional[str] = None
    assigned_hr: Optional[str] = None
    assigned_hr_user_id: Optional[str] = None
    handoff_id: Optional[str] = None
    compliance_status: str
    missing_documents_count: int
    expiring_documents_count: int
    risk_level: str


class TransferMetadataOut(BaseModel):
    handoff_id: Optional[str] = None
    handoff_at: Optional[str] = None
    handoff_by_user_id: Optional[str] = None
    handoff_by_name: Optional[str] = None
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None


class RecruiterSummaryOut(BaseModel):
    captured_at: Optional[str] = None
    candidate_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    citizenship: Optional[str] = None
    work_country: Optional[str] = None
    legal_status: Optional[str] = None
    position_category: Optional[str] = None
    vacancy_context: Optional[dict[str, Any]] = None
    notes: Optional[dict[str, Any]] = None
    document_field_values: Optional[dict[str, Any]] = None
    personal_data: Optional[dict[str, Any]] = None
    contacts: Optional[dict[str, Any]] = None


class ProfileAlertOut(BaseModel):
    code: str
    message: str


class TimelineEventOut(BaseModel):
    id: str
    occurred_at: str
    kind: str
    title: str
    detail: Optional[str] = None
    actor_id: Optional[str] = None


class EmploymentOperationalOut(BaseModel):
    id: str
    contract_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = False
    probation_end: Optional[str] = None
    position: Optional[str] = None


class WorkforceExpectedDocumentOut(BaseModel):
    document_code: str
    label: str
    group: str
    default_owner: str
    requires_expiry: bool = False
    verification_required: bool = True
    applies_to_driver: bool = True
    applies_to_non_driver: bool = True
    blocks_employment: bool = False
    renewal_window_days: int = 30
    default_next_action: str = ""
    aliases: list[str] = Field(default_factory=list)


class WorkforceDocumentControlTaskOut(BaseModel):
    document_code: str
    owner: Optional[str] = None
    next_action: Optional[str] = None
    next_due_date: Optional[str] = None
    comment: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[str] = None


class EmployeeDossierIdentityOut(BaseModel):
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    citizenship: Optional[str] = None


class EmployeeDossierLegalOut(BaseModel):
    work_country: Optional[str] = None
    legal_status: Optional[str] = None
    eligibility_status: Optional[str] = None
    requires_work_permit: Optional[bool] = None
    work_permit_valid_to: Optional[str] = None
    legal_stay_valid_to: Optional[str] = None


class EmployeeDossierDocumentsOut(BaseModel):
    linked_total: int = 0
    missing_total: int = 0
    expiring_total: int = 0
    expired_total: int = 0
    expiring_30d_total: int = 0


class EmployeeDossierQualificationsOut(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


class EmployeeDossierEmploymentOut(BaseModel):
    status: Optional[str] = None
    hire_date: Optional[str] = None
    termination_date: Optional[str] = None
    contracts_total: int = 0
    absences_total: int = 0
    leave_requests_total: int = 0
    onboarding_open_total: int = 0


class EmployeeDossierOut(BaseModel):
    identity: EmployeeDossierIdentityOut = Field(default_factory=EmployeeDossierIdentityOut)
    legal: EmployeeDossierLegalOut = Field(default_factory=EmployeeDossierLegalOut)
    documents: EmployeeDossierDocumentsOut = Field(default_factory=EmployeeDossierDocumentsOut)
    qualifications: EmployeeDossierQualificationsOut = Field(default_factory=EmployeeDossierQualificationsOut)
    employment: EmployeeDossierEmploymentOut = Field(default_factory=EmployeeDossierEmploymentOut)
    next_actions: list[dict[str, Any]] = Field(default_factory=list)


class WorkforceLifecycleEventOut(BaseModel):
    id: str
    employee_id: str
    event_code: str
    category: str
    occurred_at: str
    effective_date: Optional[str] = None
    due_date: Optional[str] = None
    owner: Optional[str] = None
    created_by: Optional[str] = None
    status: str
    dedupe_key: Optional[str] = None
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    title: str
    description: Optional[str] = None
    references: dict[str, Any] = Field(default_factory=dict)
    attachments: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class WorkforceLifecycleEventCreateIn(BaseModel):
    event_code: str
    category: str
    title: str
    occurred_at: Optional[datetime] = None
    effective_date: Optional[date] = None
    due_date: Optional[date] = None
    owner: Optional[str] = None
    created_by: Optional[str] = None
    status: Optional[str] = None
    dedupe_key: Optional[str] = None
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    description: Optional[str] = None
    references: Optional[dict[str, Any]] = None
    attachments: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None


class WorkforceLifecycleEventPatchIn(BaseModel):
    owner: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    description: Optional[str] = None
    references: Optional[dict[str, Any]] = None


class EmployeeOperationalProfileOut(BaseModel):
    """Single read-model for HR employee workspace (directory + bundle + queues + timeline)."""

    employee: EmployeeOut
    operational_summary: OperationalSummaryOut
    transfer: TransferMetadataOut
    recruiter_summary: RecruiterSummaryOut
    hire_snapshot: Optional[dict[str, Any]] = None
    documents_linked: List[CandDoc]
    documents_missing: List[dict[str, Any]] = Field(default_factory=list)
    documents_expiring: List[dict[str, Any]] = Field(default_factory=list)
    risks: List[dict[str, Any]] = Field(default_factory=list)
    alerts: List[ProfileAlertOut] = Field(default_factory=list)
    onboarding_overdue_count: int = 0
    timeline: List[TimelineEventOut] = Field(default_factory=list)
    employment_operational: List[EmploymentOperationalOut] = Field(default_factory=list)
    expected_documents: List[WorkforceExpectedDocumentOut] = Field(default_factory=list)
    document_control_tasks: List[WorkforceDocumentControlTaskOut] = Field(default_factory=list)
    employee_dossier: EmployeeDossierOut = Field(default_factory=EmployeeDossierOut)
    workforce_eligibility: dict[str, Any] = Field(default_factory=dict)
    hr_bundle: HrBundleOut


def _action_blocked_http_error(exc: WorkforceActionBlockedError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": "WORKFORCE_ACTION_BLOCKED",
            "operation": exc.operation,
            "eligibility_status": exc.eligibility_status,
            "blocking_reasons": exc.reasons,
        },
    )


def _lifecycle_out(row: Any) -> WorkforceLifecycleEventOut:
    return WorkforceLifecycleEventOut(
        id=str(row.id),
        employee_id=str(row.employee_id),
        event_code=str(row.event_code),
        category=str(row.category),
        occurred_at=row.occurred_at.isoformat() if row.occurred_at else "",
        effective_date=row.effective_date.isoformat() if row.effective_date else None,
        due_date=row.due_date.isoformat() if row.due_date else None,
        owner=row.owner,
        created_by=row.created_by,
        status=str(row.status or "open"),
        dedupe_key=row.dedupe_key,
        source_type=row.source_type,
        source_ref=row.source_ref,
        title=str(row.title or ""),
        description=row.description,
        references=row.references_json if isinstance(row.references_json, dict) else {},
        attachments=row.attachments_json if isinstance(row.attachments_json, dict) else {},
        meta=row.meta if isinstance(row.meta, dict) else {},
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


async def _sync_contract_control_tasks(
    db: AsyncSession,
    *,
    tenant_id: str,
    employment_row: WorkforceEmployment,
) -> None:
    emp_id = str(employment_row.employee_id)
    eid = str(employment_row.id)
    status = str(getattr(employment_row, "lifecycle_status", "") or "").strip().lower()
    start = getattr(employment_row, "start_date", None)
    signed = getattr(employment_row, "signed_at", None)
    expiry = getattr(employment_row, "expiry_date", None) or getattr(employment_row, "end_date", None)
    annex = str(getattr(employment_row, "latest_annex_ref", "") or "").strip()

    unsigned_due = start or date.today()
    unsigned_open = signed is None and status not in ("terminated",)
    await doc_task_svc.upsert_document_control_task(
        db,
        tenant_id=tenant_id,
        employee_id=emp_id,
        document_code=f"contract:{eid}:unsigned",
        patch={
            "owner": "HR",
            "next_action": "Obtain signature",
            "next_due_date": unsigned_due,
            "status": "open" if unsigned_open else "done",
            "comment": "Blocking: yes",
        },
    )

    exp_open = False
    exp_due = None
    if expiry and status in ("issued", "signed", "active", "expiring", "renewed"):
        days_left = (expiry - date.today()).days
        if days_left <= 30:
            exp_open = True
            exp_due = expiry - timedelta(days=14)
    await doc_task_svc.upsert_document_control_task(
        db,
        tenant_id=tenant_id,
        employee_id=emp_id,
        document_code=f"contract:{eid}:expiring",
        patch={
            "owner": "HR",
            "next_action": "Renew contract",
            "next_due_date": exp_due,
            "status": "open" if exp_open else "done",
            "comment": "Blocking: yes" if exp_open else None,
        },
    )

    annex_open = status in ("renewed",) and not annex
    await doc_task_svc.upsert_document_control_task(
        db,
        tenant_id=tenant_id,
        employee_id=emp_id,
        document_code=f"contract:{eid}:missing_annex",
        patch={
            "owner": "HR/legal",
            "next_action": "Upload annex",
            "next_due_date": None,
            "status": "open" if annex_open else "done",
            "comment": "Optional",
        },
    )


def _employment_out(row: Any) -> EmploymentOut:
    return EmploymentOut(
        id=row.id,
        employee_id=row.employee_id,
        contract_type=row.contract_type,
        lifecycle_status=str(row.lifecycle_status or "issued"),
        employer_name=row.employer_name,
        rate_model=row.rate_model,
        schedule=row.schedule,
        start_date=row.start_date,
        end_date=row.end_date,
        probation_end=row.probation_end,
        signed_at=row.signed_at,
        latest_annex_ref=row.latest_annex_ref,
        expiry_date=row.expiry_date,
        next_action=row.next_action,
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


def _hr_bundle_out(bundle: dict[str, Any]) -> HrBundleOut:
    summ = bundle.get("hr_document_context_summary") or {}
    items_orm: list[Any] = list(summ.get("items") or [])
    return HrBundleOut(
        employments=[_employment_out(r) for r in bundle["employments"]],
        payroll_profile=_payroll_out(bundle["payroll_profile"]) if bundle.get("payroll_profile") else None,
        zus_profile=_zus_out(bundle["zus_profile"]) if bundle.get("zus_profile") else None,
        onboarding_tasks=[_task_out(r) for r in bundle["onboarding_tasks"]],
        absences=[_absence_out(r) for r in bundle["absences"]],
        leave_requests=[_leave_out(r) for r in bundle["leave_requests"]],
        tax_profile=WorkforceTaxProfileOut.model_validate(bundle["tax_profile"])
        if bundle.get("tax_profile")
        else None,
        insurance_profile=WorkforceInsuranceProfileOut.model_validate(bundle["insurance_profile"])
        if bundle.get("insurance_profile")
        else None,
        work_eligibility_profile=WorkforceWorkEligibilityProfileOut.model_validate(bundle["work_eligibility_profile"])
        if bundle.get("work_eligibility_profile")
        else None,
        work_eligibility_payment_requirements=[
            WorkforceWorkEligibilityPaymentRequirementOut.from_orm_row(r)
            for r in (bundle.get("work_eligibility_payment_requirements") or [])
        ],
        compliance_state=WorkforceComplianceStateOut.model_validate(bundle["compliance_state"])
        if bundle.get("compliance_state")
        else None,
        hr_document_context_summary=WorkforceHrDocumentContextSummaryOut(
            total=int(summ.get("total") or 0),
            by_context_type=dict(summ.get("by_context_type") or {}),
            items=[WorkforceHrDocumentContextOut.model_validate(x) for x in items_orm],
        ),
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
    "/employees/directory",
    response_model=EmployeeDirectoryPageOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def list_employees_directory_endpoint(
    status: Optional[str] = Query(None),
    compliance_status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    missing_docs: Optional[bool] = Query(None),
    expiring_docs: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> EmployeeDirectoryPageOut:
    db, tid = db_tenant
    items_raw, total = await wf_directory.list_employees_directory(
        db,
        tenant_id=str(tid),
        viewer=ctx,
        status=status,
        compliance_status=compliance_status,
        risk_level=risk_level,
        missing_docs=missing_docs,
        expiring_docs=expiring_docs,
        search=search,
        limit=limit,
        offset=offset,
    )
    return EmployeeDirectoryPageOut(
        items=[EmployeeDirectoryRowOut.model_validate(r) for r in items_raw],
        total=total,
    )


@router.get(
    "/employees/by-candidate/{candidate_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee_by_candidate(
    candidate_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmployeeOut:
    """Resolve workforce employee linked to a recruitment candidate (PR17.4)."""
    db, tid = db_tenant
    tenant_id = str(tid)
    await ensure_candidate_access(db, tenant_id, candidate_id, current_user)
    row = await we_svc.find_employee_by_candidate(db, tenant_id, candidate_id)
    if not row:
        raise HTTPException(status_code=404, detail="workforce_employee_not_found")
    status_l = str(getattr(row, "status", "") or "").strip().lower()
    if status_l in ("returned_to_recruitment", "returned", "terminated"):
        raise HTTPException(status_code=404, detail="workforce_employee_not_active")
    return EmployeeOut.from_orm_row(row)


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
    return _hr_bundle_out(bundle)


@router.get(
    "/employees/{employee_id}/operational-profile",
    response_model=EmployeeOperationalProfileOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee_operational_profile(
    employee_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> EmployeeOperationalProfileOut:
    """HR employee workspace read-model: one response for summary, compliance, documents, bundle, timeline."""
    db, tid = db_tenant
    tenant_id = str(tid)
    raw = await wf_op.collect_operational_profile_raw(
        db, tenant_id=tenant_id, viewer=ctx, employee_id=employee_id
    )
    if not raw:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp = raw["employee"]
    bundle = raw["bundle"]
    cid = (emp.candidate_id or "").strip()
    doc_rows: list[Any] = []
    if cid:
        doc_rows = await documents_crud.list_candidate_documents(
            db,
            tenant_id,
            cid,
            active_own_company_id=own_company_id,
        )
    cand_docs = [
        build_workforce_cand_doc(
            r,
            tenant_id=tenant_id,
            workforce_employee_id=employee_id,
        )
        for r in doc_rows
    ]
    hb = _hr_bundle_out(bundle)
    return EmployeeOperationalProfileOut(
        employee=EmployeeOut.from_orm_row(emp),
        operational_summary=OperationalSummaryOut.model_validate(raw["operational_summary"]),
        transfer=TransferMetadataOut.model_validate(raw["transfer"]),
        recruiter_summary=RecruiterSummaryOut.model_validate(raw["recruiter_summary"]),
        hire_snapshot=raw.get("hire_snapshot"),
        documents_linked=cand_docs,
        documents_missing=list(raw.get("documents_missing") or []),
        documents_expiring=list(raw.get("documents_expiring") or []),
        risks=list(raw.get("risks") or []),
        alerts=[ProfileAlertOut.model_validate(a) for a in raw.get("alerts") or []],
        onboarding_overdue_count=int(raw.get("onboarding_overdue_count") or 0),
        timeline=[TimelineEventOut.model_validate(ev) for ev in raw.get("timeline") or []],
        employment_operational=[
            EmploymentOperationalOut.model_validate(e) for e in raw.get("employment_operational") or []
        ],
        expected_documents=[
            WorkforceExpectedDocumentOut.model_validate(x) for x in raw.get("expected_documents") or []
        ],
        document_control_tasks=[
            WorkforceDocumentControlTaskOut.model_validate(x)
            for x in raw.get("document_control_tasks") or []
        ],
        employee_dossier=EmployeeDossierOut.model_validate(raw.get("employee_dossier") or {}),
        workforce_eligibility=dict(raw.get("workforce_eligibility") or {}),
        hr_bundle=hb,
    )


@router.get(
    "/employees/{employee_id}/lifecycle-ledger",
    response_model=List[WorkforceLifecycleEventOut],
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def list_employee_lifecycle_ledger(
    employee_id: str,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    occurred_from: Optional[date] = Query(None),
    occurred_to: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> List[WorkforceLifecycleEventOut]:
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    rows = await ledger_svc.list_events(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        category=category,
        status=status,
        owner=owner,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
        offset=offset,
    )
    return [_lifecycle_out(x) for x in rows]


@router.post(
    "/employees/{employee_id}/lifecycle-ledger",
    response_model=WorkforceLifecycleEventOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def create_employee_lifecycle_event(
    employee_id: str,
    payload: WorkforceLifecycleEventCreateIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkforceLifecycleEventOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        row = await ledger_svc.create_event(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            event_code=payload.event_code,
            category=payload.category,
            title=payload.title,
            occurred_at=payload.occurred_at,
            effective_date=payload.effective_date,
            due_date=payload.due_date,
            owner=payload.owner,
            created_by=payload.created_by,
            status=payload.status,
            dedupe_key=payload.dedupe_key,
            source_type=payload.source_type,
            source_ref=payload.source_ref,
            description=payload.description,
            references=payload.references,
            attachments=payload.attachments,
            meta=payload.meta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _lifecycle_out(row)


@router.patch(
    "/employees/{employee_id}/lifecycle-ledger/{event_id}",
    response_model=WorkforceLifecycleEventOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_employee_lifecycle_event(
    employee_id: str,
    event_id: str,
    payload: WorkforceLifecycleEventPatchIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkforceLifecycleEventOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    row = await ledger_svc.patch_event(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        event_id=event_id,
        patch=payload.model_dump(exclude_unset=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lifecycle event not found")
    return _lifecycle_out(row)


@router.patch(
    "/employees/{employee_id}/document-control-tasks/{document_code}",
    response_model=WorkforceDocumentControlTaskOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_document_control_task(
    employee_id: str,
    document_code: str,
    payload: HrDocumentControlTaskPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkforceDocumentControlTaskOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    row = await doc_task_svc.upsert_document_control_task(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        document_code=document_code,
        patch=payload.model_dump(exclude_unset=True),
    )
    return WorkforceDocumentControlTaskOut(
        document_code=str(row.document_code or ""),
        owner=row.owner,
        next_action=row.next_action,
        next_due_date=row.next_due_date.isoformat() if row.next_due_date else None,
        comment=row.comment,
        status=row.status,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
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
    return [
        build_workforce_cand_doc(
            r,
            tenant_id=tenant_id,
            workforce_employee_id=employee_id,
        )
        for r in rows
    ]


class HrOperationalContextOut(BaseModel):
    hr_case: dict[str, Any]
    document_links: list[dict[str, Any]]


class EmployeeDocumentHrReviewIn(BaseModel):
    decision: str
    comment: Optional[str] = None
    reason_code: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class EmployeeDocumentHrReviewOut(BaseModel):
    id: str
    document_id: str
    decision: str
    comment: Optional[str] = None
    reason_code: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    reviewer_id: Optional[str] = None
    created_at: Optional[str] = None


@router.get(
    "/employees/{employee_id}/hr-operational-context",
    response_model=HrOperationalContextOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee_hr_operational_context(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> HrOperationalContextOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    bundle = await hr_ctx_svc.get_hr_operational_context_bundle(db, tenant_id, emp)
    await db.commit()
    return HrOperationalContextOut.model_validate(bundle)


@router.post(
    "/employees/{employee_id}/documents/{document_id}/hr-review",
    response_model=EmployeeDocumentHrReviewOut,
    dependencies=[Depends(require_roles(*HR_DOCUMENT_REVIEW_ROLES))],
)
async def post_employee_document_hr_review(
    employee_id: str,
    document_id: str,
    body: EmployeeDocumentHrReviewIn,
    current_user: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> EmployeeDocumentHrReviewOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        result = await hr_ctx_svc.submit_employee_document_hr_review(
            db,
            tenant_id=tenant_id,
            employee=emp,
            document_id=document_id,
            reviewer_id=str(getattr(current_user, "sub", "") or "") or None,
            decision=body.decision,
            comment=body.comment,
            reason_code=body.reason_code,
            payload=body.payload,
        )
    except ValueError as exc:
        code = str(exc)
        if code in {"DOCUMENT_NOT_FOUND", "EMPLOYEE_CANDIDATE_MISSING"}:
            raise HTTPException(status_code=404, detail=code) from exc
        if code == "DOCUMENT_NOT_ACCESSIBLE":
            raise HTTPException(status_code=403, detail=code) from exc
        if code == "INVALID_DECISION":
            raise HTTPException(status_code=422, detail=code) from exc
        raise HTTPException(status_code=422, detail=code) from exc
    await db.commit()
    return EmployeeDocumentHrReviewOut.model_validate(result)


@router.get(
    "/employees/{employee_id}/documents/{document_id}/file",
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee_document_file(
    employee_id: str,
    document_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    """Stream linked candidate document for HR workspace (Bearer auth; resolver-chosen route)."""
    return await stream_workforce_employee_document_file(
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
        workforce_employee_id=employee_id,
        document_id=document_id,
        surface="hr_workforce_employee",
    )


@router.post(
    "/employees",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def create_employee_endpoint(
    payload: EmployeeCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmployeeOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    row = await we_svc.create_employee(
        db,
        tenant_id,
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
        pipeline_stage=payload.pipeline_stage,
        initial_insurance_zus_registration_type=payload.initial_insurance_zus_registration_type,
        initial_insurance_status=payload.initial_insurance_status,
        initial_eligibility_status=payload.initial_eligibility_status,
    )
    try:
        hired_on = payload.hire_date or date.today()
        await ledger_svc.create_event(
            db,
            tenant_id=tenant_id,
            employee_id=str(row.id),
            event_code="employee_hired",
            category="employment",
            title="Employee hired",
            effective_date=hired_on,
            occurred_at=datetime.now(timezone.utc),
            owner="HR",
            created_by=str(current_user.sub),
            status="done",
            dedupe_key=f"employee_hired:{row.id}:{hired_on.isoformat()}",
            source_type="workforce_employee_create",
            source_ref=str(row.id),
            references={"employee_id": str(row.id)},
        )
    except Exception:
        logger.exception("ledger employee_hired emit failed employee=%s", getattr(row, "id", None))
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
    if became_terminated or term_date_changed:
        try:
            term_day = row.termination_date or date.today()
            await ledger_svc.create_event(
                db,
                tenant_id=str(tid),
                employee_id=str(row.id),
                event_code="employee_terminated",
                category="employment",
                title="Employee terminated",
                effective_date=term_day,
                occurred_at=datetime.now(timezone.utc),
                owner="HR",
                created_by=str(current_user.sub),
                status="done",
                dedupe_key=f"employee_terminated:{row.id}:{term_day.isoformat()}",
                source_type="workforce_employee_patch",
                source_ref=str(row.id),
                references={"employee_id": str(row.id)},
            )
            await db.commit()
        except Exception:
            logger.exception("ledger employee_terminated emit failed employee=%s", employee_id)
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
    try:
        await assert_operation_allowed(
            db,
            tenant_id=tenant_id,
            operation="hr_handoff",
            actor_id=str(current_user.sub or "").strip() or None,
            candidate=c,
            stage="recruitment",
        )
    except WorkforceActionBlockedError as exc:
        raise _action_blocked_http_error(exc) from exc
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
    try:
        row = await wh_sat.patch_payroll_profile(db, tenant_id, employee_id, data)
    except wh_sat.DownstreamIdentityBlockedError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": exc.result.block_code,
                "consumer": exc.result.consumer,
                "projection_status": exc.result.projection_status,
                "message": exc.result.message,
            },
        ) from exc
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


@router.patch(
    "/employees/{employee_id}/tax-profile",
    response_model=WorkforceTaxProfileOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_tax_profile_endpoint(
    employee_id: str,
    payload: TaxProfilePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkforceTaxProfileOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_tax_profile(db, tenant_id, employee_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Employee or tax profile not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.tax_profile_patch",
        actor_id=current_user.sub,
        target_type="workforce_tax_profile",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return WorkforceTaxProfileOut.model_validate(row)


@router.patch(
    "/employees/{employee_id}/insurance-profile",
    response_model=WorkforceInsuranceProfileOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_insurance_profile_endpoint(
    employee_id: str,
    payload: InsuranceProfilePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkforceInsuranceProfileOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_insurance_profile(
        db, tenant_id, employee_id, data, audit_actor_id=str(current_user.sub)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Employee or insurance profile not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.insurance_profile_patch",
        actor_id=current_user.sub,
        target_type="workforce_insurance_profile",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    try:
        await ledger_svc.create_event(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            event_code="insurance_changed",
            category="payroll",
            title="Insurance changed",
            occurred_at=datetime.now(timezone.utc),
            owner="Payroll",
            created_by=str(current_user.sub),
            status="done",
            dedupe_key=f"insurance_changed:{employee_id}:{row.updated_at.isoformat() if row.updated_at else ''}",
            source_type="insurance_profile_patch",
            source_ref=str(row.id),
            references={"insurance_profile_id": str(row.id), "employee_id": employee_id},
        )
    except Exception:
        logger.exception("ledger insurance_changed emit failed employee=%s", employee_id)
    await db.commit()
    await db.refresh(row)
    return WorkforceInsuranceProfileOut.model_validate(row)


@router.patch(
    "/employees/{employee_id}/work-eligibility",
    response_model=WorkforceWorkEligibilityProfileOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_work_eligibility_profile_endpoint(
    employee_id: str,
    payload: WorkEligibilityProfilePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkforceWorkEligibilityProfileOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    try:
        row = await wel_svc.patch_work_eligibility_profile(db, tenant_id, employee_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if not row:
        raise HTTPException(status_code=404, detail="Employee or work eligibility profile not found")
    await ensure_zus_registration_task(
        db, employee_id, actor_id=str(current_user.sub), source="work_eligibility_profile"
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.work_eligibility_profile_patch",
        actor_id=current_user.sub,
        target_type="workforce_work_eligibility_profile",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    try:
        app_status = str(getattr(row, "work_permit_application_status", "") or "").strip().lower()
        submitted = bool(getattr(row, "work_permit_submitted_at", None)) or app_status in ("submitted", "in_progress")
        approved = bool(getattr(row, "work_permit_received_at", None)) or app_status in ("approved", "granted")
        if submitted:
            eff = getattr(row, "work_permit_submitted_at", None) or date.today()
            await ledger_svc.create_event(
                db,
                tenant_id=tenant_id,
                employee_id=employee_id,
                event_code="permit_requested",
                category="legal",
                title="Work permit requested",
                occurred_at=datetime.now(timezone.utc),
                effective_date=eff,
                owner="External legal",
                created_by=str(current_user.sub),
                status="done",
                dedupe_key=f"permit_requested:{employee_id}:{eff.isoformat()}",
                source_type="work_eligibility_patch",
                source_ref=str(row.id),
                references={"work_eligibility_profile_id": str(row.id), "employee_id": employee_id},
            )
        if approved:
            eff2 = getattr(row, "work_permit_received_at", None) or date.today()
            await ledger_svc.create_event(
                db,
                tenant_id=tenant_id,
                employee_id=employee_id,
                event_code="permit_approved",
                category="legal",
                title="Work permit approved",
                occurred_at=datetime.now(timezone.utc),
                effective_date=eff2,
                owner="External legal",
                created_by=str(current_user.sub),
                status="done",
                dedupe_key=f"permit_approved:{employee_id}:{eff2.isoformat()}",
                source_type="work_eligibility_patch",
                source_ref=str(row.id),
                references={"work_eligibility_profile_id": str(row.id), "employee_id": employee_id},
            )
    except Exception:
        logger.exception("ledger permit events emit failed employee=%s", employee_id)
    await db.commit()
    await db.refresh(row)
    return WorkforceWorkEligibilityProfileOut.model_validate(row)


@router.get(
    "/employees/{employee_id}/work-eligibility/journey",
    response_model=WorkEligibilityJourneyOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_work_eligibility_journey_endpoint(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkEligibilityJourneyOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    payload = await build_work_eligibility_journey(db, tenant_id, employee_id)
    return WorkEligibilityJourneyOut.model_validate(payload)


@router.patch(
    "/employees/{employee_id}/work-eligibility/payment-requirements/{requirement_id}",
    response_model=WorkforceWorkEligibilityPaymentRequirementOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_work_eligibility_payment_requirement_endpoint(
    employee_id: str,
    requirement_id: str,
    payload: WorkEligibilityPaymentRequirementPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkforceWorkEligibilityPaymentRequirementOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wel_pay_svc.patch_payment_requirement(db, tenant_id, employee_id, requirement_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Payment requirement not found")
    await ensure_zus_registration_task(
        db, employee_id, actor_id=str(current_user.sub), source="work_eligibility_payment"
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.work_eligibility_payment_requirement_patch",
        actor_id=current_user.sub,
        target_type="workforce_work_eligibility_payment_requirement",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return WorkforceWorkEligibilityPaymentRequirementOut.from_orm_row(row)


@router.patch(
    "/employees/{employee_id}/compliance-state",
    response_model=WorkforceComplianceStateOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_compliance_state_endpoint(
    employee_id: str,
    payload: ComplianceStatePatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> WorkforceComplianceStateOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_compliance_state(db, tenant_id, employee_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Employee or compliance state not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.compliance_state_patch",
        actor_id=current_user.sub,
        target_type="workforce_compliance_state",
        target_id=row.id,
        payload={"employee_id": employee_id},
    )
    await db.commit()
    await db.refresh(row)
    return WorkforceComplianceStateOut.model_validate(row)


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
    try:
        effective = row.start_date or date.today()
        await ledger_svc.create_event(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            event_code="contract_issued",
            category="employment",
            title="Contract issued",
            occurred_at=datetime.now(timezone.utc),
            effective_date=effective,
            due_date=row.expiry_date or row.end_date,
            owner="HR",
            created_by=str(current_user.sub),
            status="done",
            dedupe_key=f"contract_issued:{row.id}",
            source_type="workforce_employment_create",
            source_ref=str(row.id),
            references={"employment_id": str(row.id), "employee_id": employee_id},
        )
    except Exception:
        logger.exception("ledger contract_issued emit failed employment=%s", getattr(row, "id", ""))
    try:
        await _sync_contract_control_tasks(db, tenant_id=tenant_id, employment_row=row)
    except Exception:
        logger.exception("contract control tasks sync failed employment=%s", getattr(row, "id", ""))
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
    prev = (
        await db.execute(
            select(WorkforceEmployment).where(
                WorkforceEmployment.id == employment_id,
                WorkforceEmployment.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    data = payload.model_dump(exclude_unset=True)
    row = await wh_sat.patch_employment(db, tenant_id, employment_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="Employment not found")
    if "end_date" in data and "expiry_date" not in data and row.end_date:
        row.expiry_date = row.end_date
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.employment_patch",
        actor_id=current_user.sub,
        target_type="workforce_employment",
        target_id=row.id,
        payload={},
    )
    try:
        prev_status = str(getattr(prev, "lifecycle_status", "") or "").strip().lower()
        new_status = str(getattr(row, "lifecycle_status", "") or "").strip().lower()
        prev_signed = getattr(prev, "signed_at", None)
        new_signed = getattr(row, "signed_at", None)
        expiry = row.expiry_date or row.end_date

        if prev_signed is None and new_signed is not None:
            await ledger_svc.create_event(
                db,
                tenant_id=tenant_id,
                employee_id=str(row.employee_id),
                event_code="contract_signed",
                category="employment",
                title="Contract signed",
                occurred_at=datetime.now(timezone.utc),
                effective_date=new_signed,
                due_date=expiry,
                owner="HR",
                created_by=str(current_user.sub),
                status="done",
                dedupe_key=f"contract_signed:{row.id}:{new_signed.isoformat()}",
                source_type="workforce_employment_patch",
                source_ref=str(row.id),
                references={"employment_id": str(row.id), "employee_id": str(row.employee_id)},
            )

        if prev_status != "renewed" and new_status == "renewed":
            await ledger_svc.create_event(
                db,
                tenant_id=tenant_id,
                employee_id=str(row.employee_id),
                event_code="contract_renewed",
                category="employment",
                title="Contract renewed",
                occurred_at=datetime.now(timezone.utc),
                effective_date=(row.start_date or date.today()),
                due_date=expiry,
                owner="HR",
                created_by=str(current_user.sub),
                status="done",
                dedupe_key=f"contract_renewed:{row.id}:{(expiry.isoformat() if expiry else 'na')}",
                source_type="workforce_employment_patch",
                source_ref=str(row.id),
                references={"employment_id": str(row.id), "employee_id": str(row.employee_id)},
            )

        if prev_status != "terminated" and new_status == "terminated":
            await ledger_svc.create_event(
                db,
                tenant_id=tenant_id,
                employee_id=str(row.employee_id),
                event_code="contract_terminated",
                category="employment",
                title="Contract terminated",
                occurred_at=datetime.now(timezone.utc),
                effective_date=(row.end_date or date.today()),
                owner="HR",
                created_by=str(current_user.sub),
                status="done",
                dedupe_key=f"contract_terminated:{row.id}:{(row.end_date.isoformat() if row.end_date else 'na')}",
                source_type="workforce_employment_patch",
                source_ref=str(row.id),
                references={"employment_id": str(row.id), "employee_id": str(row.employee_id)},
            )

        if expiry and new_status in ("active", "signed", "issued", "expiring", "renewed"):
            days_left = (expiry - date.today()).days
            if days_left <= 30:
                await ledger_svc.create_event(
                    db,
                    tenant_id=tenant_id,
                    employee_id=str(row.employee_id),
                    event_code="contract_expiring",
                    category="employment",
                    title="Contract expiring soon",
                    occurred_at=datetime.now(timezone.utc),
                    effective_date=expiry,
                    due_date=expiry,
                    owner="HR",
                    created_by=str(current_user.sub),
                    status="open",
                    dedupe_key=f"contract_expiring:{row.id}:{expiry.isoformat()}",
                    source_type="workforce_employment_patch",
                    source_ref=str(row.id),
                    references={"employment_id": str(row.id), "employee_id": str(row.employee_id)},
                    description=f"Contract expires in {max(days_left, 0)} day(s).",
                )
                if not (row.next_action or "").strip():
                    row.next_action = "renew contract"
                if new_status not in ("terminated", "renewed"):
                    row.lifecycle_status = "expiring"
    except Exception:
        logger.exception("ledger contract events emit failed employment=%s", employment_id)
    try:
        await _sync_contract_control_tasks(db, tenant_id=tenant_id, employment_row=row)
    except Exception:
        logger.exception("contract control tasks sync failed employment=%s", employment_id)
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
    prev = (
        await db.execute(
            select(WorkforceLeaveRequest).where(
                WorkforceLeaveRequest.id == leave_id,
                WorkforceLeaveRequest.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    prev_status = str(prev.status or "").strip().lower() if prev else ""
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
    try:
        new_status = str(row.status or "").strip().lower()
        leave_type = str(row.leave_type or "").strip().lower()
        if prev_status != "approved" and new_status == "approved" and leave_type in ("vacation", "annual_leave"):
            eff = row.start_date or date.today()
            await ledger_svc.create_event(
                db,
                tenant_id=tenant_id,
                employee_id=str(row.employee_id),
                event_code="vacation_approved",
                category="leave",
                title="Vacation approved",
                occurred_at=datetime.now(timezone.utc),
                effective_date=eff,
                owner="HR",
                created_by=str(current_user.sub),
                status="done",
                dedupe_key=f"vacation_approved:{row.id}",
                source_type="leave_request_patch",
                source_ref=str(row.id),
                references={"leave_request_id": str(row.id), "employee_id": str(row.employee_id)},
            )
    except Exception:
        logger.exception("ledger vacation_approved emit failed leave=%s", leave_id)
    await db.commit()
    await db.refresh(row)
    return _leave_out(row)


def _hr_review_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, hr_review_svc.HrReviewBlockedError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "HR_REVIEW_BLOCKED",
                "blockers": exc.blockers,
                "failed_checklist_items": exc.failed_items,
            },
        )
    msg = str(exc)
    if msg == "EMPLOYEE_NOT_FOUND":
        return HTTPException(status_code=404, detail=msg)
    if msg in (
        "HR_REVIEW_TERMINAL",
        "INVALID_CHECKLIST_ITEM",
        "RETURN_REASON_REQUIRED",
        "REJECT_REASON_REQUIRED",
        "CORRECTIONS_NOTE_REQUIRED",
        "CHECKLIST_REQUIRES_DOCUMENT_VERIFICATION",
        "VERIFICATION_NOT_FOUND",
        "DOCUMENT_MISSING",
        "HR_REVIEW_NOT_FOUND",
        "INVALID_FIELD_CODE",
        "VERIFIED_VALUE_REQUIRED",
        "OVERRIDE_REASON_REQUIRED",
        "CRITICAL_VERIFIED_FIELDS_INCOMPLETE",
        "CRITICAL_VERIFIED_FIELDS_CONFLICT",
        "CANNOT_WAIVE_HARD_BLOCKER",
        "WAIVER_REASON_REQUIRED",
        "DOCUMENT_NAME_REQUIRED",
    ):
        return HTTPException(status_code=422, detail={"code": msg})
    return HTTPException(status_code=422, detail=msg)


async def _employee_hr_review_for_verification(
    db: AsyncSession, tenant_id: str, employee_id: str
):
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    return await hr_review_svc.ensure_hr_review_for_employee(db, tenant_id, emp)


@router.get(
    "/employees/{employee_id}/hr-review/document-verifications",
    response_model=list[HrReviewDocumentRowOut],
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def list_employee_document_verifications(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> list[HrReviewDocumentRowOut]:
    db, tid = db_tenant
    tenant_id = str(tid)
    panel = await hr_review_svc.build_hr_review_panel(db, tenant_id, employee_id)
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return [HrReviewDocumentRowOut.model_validate(d) for d in panel.get("documents_for_approval") or []]


@router.post(
    "/employees/{employee_id}/hr-review/document-verifications/{document_key:path}/opened",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_document_opened(
    employee_id: str,
    document_key: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await doc_verify_svc.mark_document_opened(
            db, tenant_id=tenant_id, review=review, document_key=document_key, actor_user_id=actor
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/document-verifications/{document_key:path}/reviewed",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_document_reviewed(
    employee_id: str,
    document_key: str,
    body: HrDocumentReviewedFieldsIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await doc_verify_svc.save_document_reviewed_fields(
            db,
            tenant_id=tenant_id,
            review=review,
            document_key=document_key,
            actor_user_id=actor,
            reviewed_fields=body.reviewed_fields,
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/document-verifications/{document_key:path}/verify",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_document_verify(
    employee_id: str,
    document_key: str,
    body: HrDocumentReviewedFieldsIn | None = None,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await doc_verify_svc.verify_document(
            db,
            tenant_id=tenant_id,
            review=review,
            document_key=document_key,
            actor_user_id=actor,
            reviewed_fields=body.reviewed_fields if body else None,
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/document-verifications/{document_key:path}/reject",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_document_reject(
    employee_id: str,
    document_key: str,
    body: HrDocumentRejectIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await doc_verify_svc.reject_document(
            db,
            tenant_id=tenant_id,
            review=review,
            document_key=document_key,
            actor_user_id=actor,
            reason=body.reason,
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/document-verifications/{document_key:path}/request-correction",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_document_request_correction(
    employee_id: str,
    document_key: str,
    body: HrDocumentCorrectionIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await doc_verify_svc.request_document_correction(
            db,
            tenant_id=tenant_id,
            review=review,
            document_key=document_key,
            actor_user_id=actor,
            note=body.note,
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/document-verifications/{document_key:path}/waive-requirement",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_document_waive_requirement(
    employee_id: str,
    document_key: str,
    body: HrDocumentRequirementWaiverIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await doc_verify_svc.waive_document_requirement(
            db,
            tenant_id=tenant_id,
            review=review,
            document_key=document_key,
            actor_user_id=actor,
            reason=body.reason,
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/additional-document-request",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_hr_additional_document_request(
    employee_id: str,
    body: HrAdditionalDocumentRequestIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await hr_review_svc.add_hr_requested_document(
            db,
            tenant_id,
            review,
            document_name=body.document_name,
            note=body.note,
            urgency=body.urgency,
            actor_user_id=actor,
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.get(
    "/employees/{employee_id}/trusted-identity/prep-status",
    response_model=TrustedIdentityPrepStatusOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee_trusted_identity_prep_status(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TrustedIdentityPrepStatusOut:
    from backend.app.services.trusted_identity_prep_status import build_trusted_identity_prep_status

    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    payload = await build_trusted_identity_prep_status(
        db, tenant_id=tenant_id, employee_id=employee_id
    )
    await db.commit()
    return TrustedIdentityPrepStatusOut.model_validate(payload)


def _contract_generation_http_error(exc: Exception) -> HTTPException:
    from backend.app.services.employment_identity_read_adapter import TrustedIdentityAccessError

    if isinstance(exc, TrustedIdentityAccessError):
        return HTTPException(
            status_code=422,
            detail={
                "code": exc.code,
                "consumer": exc.consumer,
                "projection_status": exc.projection_status,
                "review_id": exc.review_id,
                "message": str(exc),
            },
        )
    msg = str(exc)
    if msg.startswith("CONTRACT_TEMPLATE_UNTRUSTED_PLACEHOLDERS:"):
        placeholders = msg.split(":", 1)[1].split(",") if ":" in msg else []
        return HTTPException(
            status_code=422,
            detail={
                "code": "CONTRACT_TEMPLATE_UNTRUSTED_PLACEHOLDERS",
                "placeholders": [p for p in placeholders if p],
            },
        )
    if msg in (
        "EMPLOYEE_NOT_FOUND",
        "EMPLOYEE_CANDIDATE_REQUIRED_FOR_DOCUMENT",
        "template_not_found",
        "CONTRACT_TEMPLATE_IDENTITY_OVERRIDE_FORBIDDEN",
    ):
        return HTTPException(status_code=422, detail={"code": msg})
    if msg.startswith("TRUSTED_IDENTITY_"):
        return HTTPException(status_code=422, detail={"code": msg})
    return HTTPException(status_code=400, detail=msg)


@router.post(
    "/employees/{employee_id}/contract-generation/preview",
    response_model=ContractDraftPreviewOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_contract_draft_preview(
    employee_id: str,
    body: ContractDraftPreviewIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> ContractDraftPreviewOut:
    from backend.app.services.contract_generation import generate_contract_draft_preview

    db, tid = db_tenant
    tenant_id = str(tid)
    if not body.template_id and not (body.template_code and body.template_code.strip()):
        raise HTTPException(status_code=422, detail={"code": "template_id_or_template_code_required"})
    actor = str(current_user.sub or "").strip() or None
    try:
        emp = await we_svc.get_employee(db, tenant_id, employee_id)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        await assert_operation_allowed(
            db,
            tenant_id=tenant_id,
            operation="contract_signing",
            actor_id=actor,
            employee=emp,
            stage="hr",
        )
        log, doc, meta = await generate_contract_draft_preview(
            db,
            tenant_id,
            employee_id=employee_id,
            template_id=body.template_id,
            template_code=body.template_code.strip() if body.template_code else None,
            variable_bindings=body.variable_bindings,
            triggered_by_user_id=actor,
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            action="workforce.contract_draft_preview",
            actor_id=actor,
            target_type="workforce_employee",
            target_id=employee_id,
            payload={
                "document_id": str(doc.id),
                "template_id": log.template_id,
                "log_id": log.id,
            },
        )
    except WorkforceActionBlockedError as exc:
        raise _action_blocked_http_error(exc) from exc
    except Exception as exc:
        raise _contract_generation_http_error(exc) from exc

    preview_url: str | None = None
    files = getattr(doc, "files", None) or []
    if isinstance(files, list) and files:
        first = files[0] if isinstance(files[0], dict) else None
        if first:
            preview_url = str(first.get("url") or "") or None

    await db.commit()
    return ContractDraftPreviewOut(
        log_id=str(log.id),
        document_id=str(doc.id),
        template_id=str(log.template_id) if log.template_id else None,
        status=str(log.status),
        preview_url=preview_url,
        trusted_identity_bindings=dict(meta.get("trusted_identity_bindings") or {}),
    )


@router.get(
    "/employees/{employee_id}/hr-review/verified-fields",
    response_model=list[HrVerifiedFieldOut],
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def list_employee_verified_fields(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> list[HrVerifiedFieldOut]:
    db, tid = db_tenant
    tenant_id = str(tid)
    review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
    await vf_svc.ensure_critical_field_placeholders(db, tenant_id=tenant_id, review=review, employee_id=employee_id)
    fields = await vf_svc.list_for_review(db, tenant_id, review.id)
    await db.commit()
    return [HrVerifiedFieldOut.model_validate(f) for f in fields]


@router.post(
    "/employees/{employee_id}/hr-review/verified-fields/{field_code}/override",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_verified_field_override(
    employee_id: str,
    field_code: str,
    body: HrVerifiedFieldOverrideIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        review = await _employee_hr_review_for_verification(db, tenant_id, employee_id)
        await vf_svc.override_verified_field(
            db,
            tenant_id=tenant_id,
            review=review,
            field_code=field_code,
            actor_user_id=actor,
            verified_value=body.verified_value,
            override_reason=body.override_reason,
        )
        panel = await hr_review_svc.rebuild_hr_review_panel_for_review(db, tenant_id, review)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.get(
    "/employees/{employee_id}/hr-review",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def get_employee_hr_review(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    try:
        panel = await hr_review_svc.build_hr_review_panel(db, tenant_id, employee_id)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.patch(
    "/employees/{employee_id}/hr-review/checklist/{item_code}",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def patch_employee_hr_review_checklist(
    employee_id: str,
    item_code: str,
    payload: HrReviewChecklistPatchIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        await hr_review_svc.update_hr_review_checklist_item(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            item_code=item_code,
            actor_user_id=actor,
            satisfied=payload.satisfied,
        )
        panel = await hr_review_svc.build_hr_review_panel(db, tenant_id, employee_id)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.hr_review.checklist",
        actor_id=actor,
        target_type="workforce_employee",
        target_id=employee_id,
        payload={"item_code": item_code, "satisfied": payload.satisfied},
    )
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/approve",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_hr_review_approve(
    employee_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        emp = await we_svc.get_employee(db, tenant_id, employee_id)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        await assert_operation_allowed(
            db,
            tenant_id=tenant_id,
            operation="employee_activation",
            actor_id=actor,
            employee=emp,
            stage="hr",
        )
        await hr_review_svc.approve_hr_review(
            db, tenant_id=tenant_id, employee_id=employee_id, actor_user_id=actor
        )
        panel = await hr_review_svc.build_hr_review_panel(db, tenant_id, employee_id)
    except WorkforceActionBlockedError as exc:
        raise _action_blocked_http_error(exc) from exc
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.hr_review.approve",
        actor_id=actor,
        target_type="workforce_employee",
        target_id=employee_id,
        payload={},
    )
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/return-to-recruitment",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_hr_review_return(
    employee_id: str,
    payload: HrReviewReasonIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        await hr_review_svc.return_hr_review_to_recruitment(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            actor_user_id=actor,
            return_reason=payload.reason,
        )
        panel = await hr_review_svc.build_hr_review_panel(db, tenant_id, employee_id)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.hr_review.return",
        actor_id=actor,
        target_type="workforce_employee",
        target_id=employee_id,
        payload={"reason": payload.reason[:500]},
    )
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/request-corrections",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_hr_review_corrections(
    employee_id: str,
    payload: HrReviewNoteIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        await hr_review_svc.request_hr_review_corrections(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            actor_user_id=actor,
            note=payload.note,
        )
        panel = await hr_review_svc.build_hr_review_panel(db, tenant_id, employee_id)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.hr_review.request_corrections",
        actor_id=actor,
        target_type="workforce_employee",
        target_id=employee_id,
        payload={"note": payload.note[:500]},
    )
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


@router.post(
    "/employees/{employee_id}/hr-review/reject",
    response_model=HrReviewPanelOut,
    dependencies=[Depends(require_roles(*HR_WORKSPACE_ROLES))],
)
async def post_employee_hr_review_reject(
    employee_id: str,
    payload: HrReviewReasonIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> HrReviewPanelOut:
    db, tid = db_tenant
    tenant_id = str(tid)
    actor = str(current_user.sub or "").strip()
    try:
        await hr_review_svc.reject_hr_review(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            actor_user_id=actor,
            reject_reason=payload.reason,
        )
        panel = await hr_review_svc.build_hr_review_panel(db, tenant_id, employee_id)
    except Exception as exc:
        raise _hr_review_http_error(exc) from exc
    if not panel:
        raise HTTPException(status_code=404, detail="Employee not found")
    await log_activity(
        db,
        tenant_id=tenant_id,
        action="workforce.hr_review.reject",
        actor_id=actor,
        target_type="workforce_employee",
        target_id=employee_id,
        payload={"reason": payload.reason[:500]},
    )
    await db.commit()
    return HrReviewPanelOut.model_validate(panel)


from backend.app.api.v1.workforce import zus_workspace_router as _zus_ws_router  # noqa: E402

router.include_router(_zus_ws_router.router, prefix="/zus-workspace", tags=["workforce-zus-workspace"])
