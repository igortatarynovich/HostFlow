"""HR workforce satellites — PATCH/POST payloads (storage MVP, not payroll math)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class PayrollProfilePatch(BaseModel):
    pay_type: Optional[str] = Field(default=None, max_length=64)
    base_rate: Optional[str] = Field(default=None, max_length=64, description="Decimal string, e.g. 6500.00")
    currency: Optional[str] = Field(default=None, max_length=8)
    calculation_system: Optional[str] = Field(default=None, max_length=128)
    pay_day_note: Optional[str] = Field(default=None, max_length=256)
    bank_account: Optional[str] = Field(default=None, max_length=128)
    tax_status: Optional[str] = Field(default=None, max_length=64)
    pit_declarations: Optional[dict[str, Any]] = None
    allowances: Optional[dict[str, Any]] = None
    deductions: Optional[dict[str, Any]] = None
    payroll_status: Optional[str] = Field(default=None, max_length=64)
    external_refs: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None


# --- ZUS ---
class ZusProfilePatch(BaseModel):
    registration_status: Optional[str] = Field(default=None, max_length=64)
    submitted_at: Optional[date] = None
    employment_basis: Optional[str] = Field(default=None, max_length=64)
    responsible_party: Optional[str] = Field(default=None, max_length=64)
    insurance_coverage: Optional[dict[str, Any]] = None
    forms: Optional[list[Any]] = None
    meta: Optional[dict[str, Any]] = None


# --- PR-2: legal / tax / insurance / compliance (storage; not payroll engine) ---
class TaxProfilePatch(BaseModel):
    tax_residency_country: Optional[str] = Field(default=None, max_length=8)
    tax_office: Optional[str] = Field(default=None, max_length=64)
    pit2_submitted: Optional[bool] = None
    pit2_monthly_amount: Optional[str] = Field(
        default=None, max_length=32, description="Decimal string or empty/null to clear"
    )
    tax_deductible_costs_type: Optional[str] = Field(default=None, max_length=32)
    young_person_relief: Optional[bool] = None


class InsuranceProfilePatch(BaseModel):
    zus_title_code: Optional[str] = Field(default=None, max_length=32)
    social_insurance: Optional[str] = Field(default=None, max_length=32)
    health_insurance: Optional[str] = Field(default=None, max_length=32)
    sickness_insurance: Optional[str] = Field(default=None, max_length=32)
    accident_insurance: Optional[str] = Field(default=None, max_length=32)
    zus_registration_type: Optional[str] = Field(default=None, max_length=64)
    registered_at: Optional[date] = None
    deregistered_at: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=32)


class ComplianceStatePatch(BaseModel):
    status: Optional[str] = Field(default=None, max_length=32)
    missing_count: Optional[int] = Field(default=None, ge=0)
    expired_count: Optional[int] = Field(default=None, ge=0)
    expiring_soon_count: Optional[int] = Field(default=None, ge=0)
    high_risk_count: Optional[int] = Field(default=None, ge=0)
    cannot_work: Optional[bool] = None
    last_evaluated_at: Optional[datetime] = None
    reasons: Optional[Any] = None


class WorkEligibilityProfilePatch(BaseModel):
    citizenship: Optional[str] = Field(default=None, max_length=8)
    residence_status: Optional[str] = Field(default=None, max_length=32)
    legal_stay_document_type: Optional[str] = Field(default=None, max_length=64)
    legal_stay_valid_to: Optional[date] = None
    requires_work_permit: Optional[bool] = None
    work_permit_type: Optional[str] = Field(default=None, max_length=64)
    work_permit_submission_method: Optional[str] = Field(default=None, max_length=64)
    work_permit_application_status: Optional[str] = Field(default=None, max_length=64)
    work_permit_submitted_at: Optional[date] = None
    work_permit_received_at: Optional[date] = None
    work_permit_valid_to: Optional[date] = None
    red_paper_required: Optional[bool] = None
    red_paper_status: Optional[str] = Field(default=None, max_length=32)
    eligibility_status: Optional[str] = Field(default=None, max_length=32)
    position_category: Optional[str] = Field(default=None, max_length=32)
    work_country: Optional[str] = Field(default=None, max_length=8)
    employer_country: Optional[str] = Field(default=None, max_length=8)
    contract_type: Optional[str] = Field(default=None, max_length=64)
    meta: Optional[dict[str, Any]] = None


class WorkEligibilityPaymentRequirementPatch(BaseModel):
    payment_status: Optional[str] = Field(default=None, max_length=16)
    amount: Optional[Decimal] = None
    currency: Optional[str] = Field(default=None, max_length=8)
    due_at: Optional[date] = None
    paid_at: Optional[datetime] = None
    payment_reference: Optional[str] = Field(default=None, max_length=256)
    receipt_document_id: Optional[str] = Field(default=None, max_length=36)


# --- Employment / contract ---
class EmploymentCreate(BaseModel):
    contract_type: str = Field(default="unknown", max_length=64)
    lifecycle_status: Optional[str] = Field(default="issued", max_length=32)
    employer_name: Optional[str] = Field(default=None, max_length=160)
    rate_model: Optional[dict[str, Any]] = None
    schedule: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    probation_end: Optional[date] = None
    signed_at: Optional[date] = None
    latest_annex_ref: Optional[str] = Field(default=None, max_length=160)
    expiry_date: Optional[date] = None
    next_action: Optional[str] = Field(default=None, max_length=256)
    conditions_text: Optional[str] = None
    vacancy_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class EmploymentPatch(BaseModel):
    contract_type: Optional[str] = Field(default=None, max_length=64)
    lifecycle_status: Optional[str] = Field(default=None, max_length=32)
    employer_name: Optional[str] = Field(default=None, max_length=160)
    rate_model: Optional[dict[str, Any]] = None
    schedule: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    probation_end: Optional[date] = None
    signed_at: Optional[date] = None
    latest_annex_ref: Optional[str] = Field(default=None, max_length=160)
    expiry_date: Optional[date] = None
    next_action: Optional[str] = Field(default=None, max_length=256)
    conditions_text: Optional[str] = None
    vacancy_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class OnboardingTaskPatch(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    sort_order: Optional[int] = None
    status: Optional[str] = Field(default=None, max_length=32)
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assignee_user_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class AbsenceCreate(BaseModel):
    absence_type: str = Field(..., max_length=64)
    start_date: date
    end_date: Optional[date] = None
    source: str = Field(default="manual", max_length=64)
    status: str = Field(default="reported", max_length=64)
    payer: Optional[str] = Field(default=None, max_length=32)
    payroll_impact: Optional[str] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class AbsencePatch(BaseModel):
    absence_type: Optional[str] = Field(default=None, max_length=64)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=64)
    payer: Optional[str] = Field(default=None, max_length=32)
    payroll_impact: Optional[str] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class LeaveRequestCreate(BaseModel):
    leave_type: str = Field(..., max_length=64)
    start_date: date
    end_date: date
    status: str = Field(default="pending", max_length=64)
    year_entitlement_days: Optional[str] = Field(default=None, max_length=32, description="Decimal days")
    used_days_before: Optional[str] = Field(default=None, max_length=32)
    conflict_flags: Optional[dict[str, Any]] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class LeaveRequestPatch(BaseModel):
    leave_type: Optional[str] = Field(default=None, max_length=64)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=64)
    year_entitlement_days: Optional[str] = None
    used_days_before: Optional[str] = None
    conflict_flags: Optional[dict[str, Any]] = None
    approver_user_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class HrDocumentControlTaskPatch(BaseModel):
    owner: Optional[str] = Field(default=None, max_length=64)
    next_action: Optional[str] = Field(default=None, max_length=256)
    next_due_date: Optional[date] = None
    comment: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, max_length=32)
