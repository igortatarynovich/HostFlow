from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ApplicationModule = Literal["sales", "recruitment"]
ApplicationStatus = Literal["new", "in_progress", "waiting", "completed", "rejected", "questionnaire_submitted"]
ApplicationTabBucket = Literal["all", "new", "in_progress", "waiting", "completed"]
ApplicationStageUpdate = Literal["contacted", "qualified", "lost"]


class ApplicationContactOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class ApplicationOut(BaseModel):
    """Product-facing inbound object. UI must use this — never Lead."""

    model_config = ConfigDict(extra="forbid")

    id: str
    module: ApplicationModule
    contact: ApplicationContactOut
    title: str
    subtitle: Optional[str] = None
    source: Optional[str] = None
    status: ApplicationStatus
    tab_bucket: ApplicationTabBucket
    assignee_id: Optional[str] = None
    next_action: Optional[str] = None
    last_activity_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    priority: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extensions: Dict[str, Any] = Field(default_factory=dict)
    outcome_entity_id: Optional[str] = None
    outcome_entity_type: Optional[str] = None
    # Stage 3 slice 3 — SalesInquiry product identity (Lead = transport)
    sales_inquiry_id: Optional[str] = None
    transport_lead_id: Optional[str] = None


class ApplicationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[ApplicationOut]
    total: int
    counts: Optional[Dict[str, int]] = None


class SalesInquiryDuplicateHintOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application: ApplicationOut
    match_reason: Literal["phone", "email", "phone_and_email"]


class SalesInquiryDuplicateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[SalesInquiryDuplicateHintOut]
    total: int


class SalesCapabilitySpineCapabilityOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Optional[str] = None
    source: Literal["entity_profile", "undecided"]
    decided: bool = False


class SalesCapabilitySpineReviewOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = None
    decision: Optional[Dict[str, Any]] = None
    candidates: List[Any] = Field(default_factory=list)
    convert_allowed: bool = False
    blocks_convert: bool = False
    present: bool = False
    reason: Optional[str] = None
    version: Optional[int] = None


class SalesCapabilitySpineConvertMappingOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_account_id: Optional[str] = None
    flights_ledger_id: Optional[str] = None
    destination: Optional[str] = None
    converted_at: Optional[Any] = None


class SalesCapabilitySpineConvertOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool = False
    reason: Optional[str] = None
    inquiry_status: Optional[str] = None
    client_account_id: Optional[str] = None
    mapping_present: bool = False
    mapping: Optional[SalesCapabilitySpineConvertMappingOut] = None


class SalesCapabilitySpineLineageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sales_inquiry_id: Optional[str] = None
    client_account_id: Optional[str] = None
    flights_ledger_id: Optional[str] = None
    company_id: Optional[str] = None
    destination: Optional[str] = None
    recorded_at: Optional[Any] = None
    chain: List[Any] = Field(default_factory=list)


class SalesCapabilitySpineTraceabilityOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    present: bool = False
    lineage: Optional[SalesCapabilitySpineLineageOut] = None


class SalesCapabilitySpineOut(BaseModel):
    """Read-only Pipeline v1 spine projection for Capability UI."""

    model_config = ConfigDict(extra="forbid")

    contract: str
    sales_inquiry_id: Optional[str] = None
    transport_lead_id: Optional[str] = None
    inquiry_status: Optional[str] = None
    capability: SalesCapabilitySpineCapabilityOut
    review: SalesCapabilitySpineReviewOut
    convert: SalesCapabilitySpineConvertOut
    traceability: SalesCapabilitySpineTraceabilityOut
    missing_sales_inquiry: bool = False


class ApplicationStagePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: ApplicationStageUpdate
    lost_reason_code: Optional[str] = None
    lost_reason_note: Optional[str] = None


class ApplicationIntakeDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["qualify", "reject", "pool", "request_info", "duplicate_review"]
    reason_code: Optional[str] = Field(default=None, max_length=64)
    note: Optional[str] = Field(default=None, max_length=2000)
    funnel_id: Optional[UUID] = None


class ApplicationVacancyConfirmIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID


class ApplicationFollowUpIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    due_at: Optional[str] = Field(default=None, description="ISO datetime; defaults to +1 day")
    note: Optional[str] = Field(default=None, max_length=2000)


class ApplicationAssignIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_id: str = Field(min_length=1, max_length=36)


class ApplicationCommentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=2000)


class ApplicationCallResultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: Literal[
        "no_answer",
        "answered",
        "callback_requested",
        "interested",
        "not_interested",
        "wrong_number",
        "unavailable",
    ]
    note: Optional[str] = Field(default=None, max_length=2000)
    next_contact_at: Optional[datetime] = None


class ApplicationProcessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application: ApplicationOut
    candidate_id: Optional[str] = None
    message: Optional[str] = None
