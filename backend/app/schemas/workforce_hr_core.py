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


class JourneyActionOut(BaseModel):
    """Single HR / system action surfaced on a journey step (upload, pay, open portal, …)."""

    code: str
    label: str
    href: Optional[str] = None
    document_type: Optional[str] = None
    payment_requirement_id: Optional[str] = None


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
    decision_reason: Optional[str] = None
    rule_code: Optional[str] = None
    input_facts: Optional[dict[str, Any]] = None
    confidence: Optional[float] = None
    cannot_determine_reason: Optional[str] = None
    primary_action: Optional[JourneyActionOut] = None
    secondary_actions: list[JourneyActionOut] = Field(default_factory=list)
    document_actions: list[JourneyActionOut] = Field(default_factory=list)
    payment_actions: list[JourneyActionOut] = Field(default_factory=list)


class NextHrActionOut(BaseModel):
    """Structured focal action for the HR operational rail (derived from journey)."""

    title: str
    step_code: Optional[str] = None
    step_status: Optional[str] = None
    reason: Optional[str] = None
    blockers: list[str] = Field(default_factory=list)
    cannot_determine_reason: Optional[str] = None
    primary_cta: Optional[JourneyActionOut] = None
    secondary_ctas: list[JourneyActionOut] = Field(default_factory=list)


class WorkEligibilityJourneyOut(BaseModel):
    steps: list[WorkEligibilityJourneyStepOut]
    recommended_next_action: str
    next_hr_action: Optional[NextHrActionOut] = None


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


class HrReviewChecklistItemOut(BaseModel):
    item_code: str
    label: str
    status: str
    source: str = "auto"
    required: bool = True
    blockers: list[str] = Field(default_factory=list)
    basis: dict[str, Any] = Field(default_factory=dict)
    verified_by_user_id: Optional[str] = None
    verified_at: Optional[str] = None


class HrReviewDocumentRowOut(BaseModel):
    document_key: str
    label: str
    status: str
    context_type: Optional[str] = None
    document_id: Optional[str] = None
    verified: bool = False
    expires_at: Optional[str] = None
    basis: Optional[str] = None
    open_url: Optional[str] = None
    file_url: Optional[str] = None
    document_open_context: Optional[str] = None


class HrReviewProcessStageOut(BaseModel):
    code: str
    label: str
    state: str


class HrReviewHeroOut(BaseModel):
    candidate_display_name: Optional[str] = None
    handoff_id: Optional[str] = None
    handoff_status: Optional[str] = None
    review_status: str
    vacancy_label: Optional[str] = None
    transferred_at: Optional[str] = None
    transferred_by: Optional[str] = None
    employee_status: Optional[str] = None
    has_employee: bool = False
    current_stage_code: Optional[str] = None
    current_stage_label: Optional[str] = None
    state_message: str = ""
    process_stages: list[HrReviewProcessStageOut] = Field(default_factory=list)


class HrReviewNextActionOut(BaseModel):
    title: str
    reason: str = ""
    blockers: list[str] = Field(default_factory=list)
    primary_label: Optional[str] = None
    primary_anchor: Optional[str] = None
    secondary_label: Optional[str] = None
    secondary_anchor: Optional[str] = None


class HrReviewDecisionReadinessOut(BaseModel):
    checklist_done: int = 0
    checklist_total: int = 0
    can_approve: bool = False
    approve_blocked_reason: Optional[str] = None
    post_approve_effects: list[str] = Field(default_factory=list)


class HrReviewTimelineEventOut(BaseModel):
    at: Optional[str] = None
    kind: str
    label: str


class HrReviewEligibilitySummaryOut(BaseModel):
    current_step_code: Optional[str] = None
    current_step_title: Optional[str] = None
    current_step_status: Optional[str] = None
    recommended_next_action: Optional[str] = None
    blockers: list[str] = Field(default_factory=list)
    decision_basis: Optional[Any] = None


class HrReviewTaskActionOut(BaseModel):
    label: str
    anchor: Optional[str] = None


class HrReviewRelatedDocumentOut(BaseModel):
    document_key: Optional[str] = None
    document_id: Optional[str] = None
    label: Optional[str] = None
    status: Optional[str] = None


class HrReviewCurrentTaskOut(BaseModel):
    task_type: str
    title: str
    description: str
    why: str
    priority: str = "normal"
    priority_step: int = 0
    priority_total: int = 8
    priority_catalog_label: Optional[str] = None
    blocks_approval: bool = True
    primary_action: HrReviewTaskActionOut
    secondary_actions: list[HrReviewTaskActionOut] = Field(default_factory=list)
    target_anchor: Optional[str] = None
    related_documents: list[HrReviewRelatedDocumentOut] = Field(default_factory=list)
    related_checklist_items: list[str] = Field(default_factory=list)
    completion_condition: str = ""


class HrReviewTaskPriorityStepOut(BaseModel):
    step: int
    task_type: str
    label: str
    summary: str = ""
    state: str = "idle"


class HrReviewPanelOut(BaseModel):
    review_id: str
    employee_id: Optional[str] = None
    candidate_id: Optional[str] = None
    handoff_id: Optional[str] = None
    status: str
    checklist: list[HrReviewChecklistItemOut] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    failed_required_items: list[str] = Field(default_factory=list)
    can_approve: bool = False
    next_required_action: Optional[str] = None
    decision_basis: Optional[dict[str, Any]] = None
    documents_for_approval: list[HrReviewDocumentRowOut] = Field(default_factory=list)
    corrections_note: Optional[str] = None
    return_reason: Optional[str] = None
    reject_reason: Optional[str] = None
    decided_by_user_id: Optional[str] = None
    decided_at: Optional[str] = None
    mode: Optional[str] = None
    hero: Optional[HrReviewHeroOut] = None
    next_action: Optional[HrReviewNextActionOut] = None
    decision_readiness: Optional[HrReviewDecisionReadinessOut] = None
    recent_timeline: list[HrReviewTimelineEventOut] = Field(default_factory=list)
    work_eligibility_summary: Optional[HrReviewEligibilitySummaryOut] = None
    current_task: Optional[HrReviewCurrentTaskOut] = None
    task_priority_v1: list[HrReviewTaskPriorityStepOut] = Field(default_factory=list)


class HrReviewChecklistPatchIn(BaseModel):
    satisfied: bool = True


class HrReviewNoteIn(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


class HrReviewReasonIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=4000)
