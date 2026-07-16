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


class ApplicationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[ApplicationOut]
    total: int
    counts: Optional[Dict[str, int]] = None


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


class ApplicationProcessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application: ApplicationOut
    candidate_id: Optional[str] = None
    message: Optional[str] = None
