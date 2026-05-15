"""Pydantic schemas for HR workforce core profiles (PR-1 read/API foundation)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkforceTaxProfileOut(BaseModel):
    id: str
    tenant_id: str
    employee_id: str
    tax_residency_country: Optional[str] = None
    tax_office: Optional[str] = None
    pit2_submitted: bool = False
    pit2_monthly_amount: Optional[Decimal] = None
    tax_deductible_costs_type: Optional[str] = None
    young_person_relief: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkforceInsuranceProfileOut(BaseModel):
    id: str
    tenant_id: str
    employee_id: str
    zus_title_code: Optional[str] = None
    social_insurance: Optional[str] = None
    health_insurance: Optional[str] = None
    sickness_insurance: Optional[str] = None
    accident_insurance: Optional[str] = None
    zus_registration_type: Optional[str] = None
    registered_at: Optional[date] = None
    deregistered_at: Optional[date] = None
    status: str = "draft"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkforceWorkEligibilityPaymentRequirementOut(BaseModel):
    id: str
    tenant_id: str
    employee_id: str
    requirement_type: str
    amount: Optional[str] = None
    currency: str = "PLN"
    payment_status: str = "not_required"
    due_at: Optional[date] = None
    paid_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    receipt_document_id: Optional[str] = None
    blocks_step: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: Any) -> "WorkforceWorkEligibilityPaymentRequirementOut":
        amt = getattr(row, "amount", None)
        amt_s: Optional[str] = None
        if amt is not None:
            amt_s = str(amt)
        return cls(
            id=row.id,
            tenant_id=row.tenant_id,
            employee_id=row.employee_id,
            requirement_type=row.requirement_type,
            amount=amt_s,
            currency=row.currency or "PLN",
            payment_status=row.payment_status or "not_required",
            due_at=row.due_at,
            paid_at=row.paid_at,
            payment_reference=row.payment_reference,
            receipt_document_id=row.receipt_document_id,
            blocks_step=row.blocks_step,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class WorkforceWorkEligibilityProfileOut(BaseModel):
    id: str
    tenant_id: str
    employee_id: str
    citizenship: Optional[str] = None
    residence_status: Optional[str] = None
    legal_stay_document_type: Optional[str] = None
    legal_stay_valid_to: Optional[date] = None
    requires_work_permit: Optional[bool] = None
    work_permit_type: Optional[str] = None
    work_permit_submission_method: Optional[str] = None
    work_permit_application_status: Optional[str] = None
    work_permit_submitted_at: Optional[date] = None
    work_permit_received_at: Optional[date] = None
    work_permit_valid_to: Optional[date] = None
    red_paper_required: Optional[bool] = None
    red_paper_status: Optional[str] = None
    eligibility_status: str = "not_evaluated"
    position_category: Optional[str] = None
    work_country: Optional[str] = None
    employer_country: Optional[str] = None
    contract_type: Optional[str] = None
    meta: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkEligibilityJourneyStepOut(BaseModel):
    step_code: str
    label: str
    status: str
    blockers: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    linked_payment_requirement_id: Optional[str] = None
    linked_document_id: Optional[str] = None
    action_label: Optional[str] = None
    action_url: Optional[str] = None
    external_submission_url: Optional[str] = None


class WorkEligibilityJourneyOut(BaseModel):
    steps: list[WorkEligibilityJourneyStepOut]
    recommended_next_action: str


class WorkforceHrDocumentContextOut(BaseModel):
    id: str
    tenant_id: str
    employee_id: str
    document_id: str
    context_type: str
    legal_category: Optional[str] = None
    document_group: Optional[str] = None
    required: bool = False
    verified: bool = False
    verification_status: Optional[str] = None
    expires_at: Optional[datetime] = None
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkforceComplianceStateOut(BaseModel):
    id: str
    tenant_id: str
    employee_id: str
    status: str = "not_evaluated"
    missing_count: int = 0
    expired_count: int = 0
    expiring_soon_count: int = 0
    high_risk_count: int = 0
    cannot_work: bool = False
    last_evaluated_at: Optional[datetime] = None
    reasons: Optional[Any] = Field(default=None)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkforceHrDocumentContextSummaryOut(BaseModel):
    """Aggregated HR document contexts (e-teczka / HR hub); items are capped for payload size."""

    total: int = 0
    by_context_type: dict[str, int] = Field(default_factory=dict)
    items: list[WorkforceHrDocumentContextOut] = Field(default_factory=list)
