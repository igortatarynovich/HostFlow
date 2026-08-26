from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.app.models.vacancy import EmploymentType, normalize_vacancy_status


# Phase 2.6.D Stage A — single normalizer applied to every entry/exit
# point in the vacancy schema. Aliases (`paused → on_hold`) and unknown
# values are coerced here so downstream code (NBA, list filters,
# analytics) can rely on a canonical set without repeating the rules.
def _normalize_status_field(value: Any) -> Any:
    if value is None:
        return None
    return normalize_vacancy_status(value)


class VacancyIn(BaseModel):
    company_id: UUID
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    salary_from: Optional[Union[str, int, float]] = None
    salary_to: Optional[Union[str, int, float]] = None
    currency: Optional[Union[str, int, float]] = "EUR"
    status: str = "open"
    manager: Optional[UUID] = None
    candidate_profile_id: Optional[UUID] = None
    required_documents_template_id: Optional[UUID] = None
    employment_type: EmploymentType = Field(default=EmploymentType.full_time)
    extra: Dict[str, Any] = Field(default_factory=dict)
    headcount_target: Optional[int] = Field(
        default=None,
        ge=0,
        le=9999,
        description="Planned positions to fill; omit or 0 for none",
    )
    funnel_id: Optional[UUID] = Field(
        default=None,
        description="Recruitment candidate funnel for this vacancy",
    )
    order_line_id: Optional[UUID] = Field(
        default=None,
        description="ADR-032: bind to Sales Order Line (1:1); pulls headcount from line",
    )

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        if value is None:
            return "open"
        return normalize_vacancy_status(value)


class VacancyOut(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    title: str
    description: Optional[str]
    location: Optional[str]
    salary_from: Optional[str]
    salary_to: Optional[str]
    currency: Optional[str]
    status: str
    is_open: Optional[bool] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None
    manager: Optional[str] = None
    candidate_profile_id: Optional[str] = None
    candidate_profile_name: Optional[str] = None
    required_documents_template_id: Optional[str] = None
    extra: Dict[str, Any]
    employment_type: EmploymentType
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    company_name: Optional[str] = None
    manager_short: Optional[str] = None
    manager_name: Optional[str] = None
    candidate_count: int = 0
    last_candidate_activity_at: Optional[datetime] = None
    headcount_target: Optional[int] = None
    order_line_id: Optional[str] = None
    funnel_id: Optional[str] = None

    # Phase 2.6.D Stage A — emit canonical values to clients even when
    # the row in the database still holds a legacy alias (`paused`). The
    # alembic migration in Stage B rewrites stored rows; this validator
    # protects the contract during the rollout window.
    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status_out(cls, value: Any) -> Any:
        if value is None:
            return "open"
        return normalize_vacancy_status(value)


class VacancyPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    company_id: Optional[UUID] = None
    salary_from: Optional[Union[str, int, float]] = None
    salary_to: Optional[Union[str, int, float]] = None
    currency: Optional[Union[str, int, float]] = None
    status: Optional[str] = None
    is_open: Optional[bool] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None
    employment_type: Optional[EmploymentType] = Field(default=None)
    salary_from_alt1: Optional[Union[str, int, float]] = Field(default=None, alias="min_salary")
    salary_from_alt2: Optional[Union[str, int, float]] = Field(default=None, alias="salary_min")
    salary_to_alt1: Optional[Union[str, int, float]] = Field(default=None, alias="max_salary")
    salary_to_alt2: Optional[Union[str, int, float]] = Field(default=None, alias="salary_max")
    currency_alt1: Optional[Union[str, int, float]] = Field(default=None, alias="currency_code")
    currency_alt2: Optional[Union[str, int, float]] = Field(default=None, alias="salary_currency")
    status_alt1: Optional[str] = Field(default=None, alias="state")
    status_alt2: Optional[str] = Field(default=None, alias="stage")
    manager: Optional[UUID] = None
    candidate_profile_id: Optional[UUID] = None
    required_documents_template_id: Optional[UUID] = None
    funnel_id: Optional[UUID] = None
    extra: Optional[Dict[str, Any]] = None
    headcount_target: Optional[int] = Field(
        default=None,
        ge=0,
        le=9999,
        description="Set planned headcount; send 0 or null with field present to clear",
    )
    order_line_id: Optional[UUID] = Field(
        default=None,
        description="ADR-032: bind/unbind Order Line (null clears)",
    )
    model_config = ConfigDict(validate_by_name=True)

    # Phase 2.6.D Stage A — apply normalization to all three status entry
    # points so legacy clients sending `state=paused` or `stage=paused`
    # behave identically to canonical `status=on_hold`.
    @field_validator("status", "status_alt1", "status_alt2", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        return _normalize_status_field(value)
