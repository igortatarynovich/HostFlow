from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CandidateSummary(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    manager: str | None = None


class UserSummary(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    short_id: str | None = None
    role: str | None = None

StatusLiteral = Literal["pending", "approved", "rejected"]


class CandidateDeleteRequestCreate(BaseModel):
    reason: str = Field(default="", max_length=2000)


class CandidateDeleteRequestOut(BaseModel):
    id: str
    tenant_id: str
    candidate_id: str
    requested_by: str
    supervisor_id: str
    reason: str | None = None
    status: StatusLiteral = "pending"
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    candidate: CandidateSummary | None = None
    requested_by_user: UserSummary | None = None
    supervisor_user: UserSummary | None = None


class CandidateDeleteDecision(BaseModel):
    decision: Literal["approve", "reject"] = Field(default="approve")
    comment: str | None = Field(default=None, max_length=2000)
