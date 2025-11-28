from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.models.vacancy import EmploymentType


class VacancyBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    company_id: UUID
    location: Optional[str] = Field(None, max_length=255)
    employment_type: Optional[EmploymentType] = Field(None)
    is_active: bool = True
    is_archived: bool = False

    model_config = {"from_attributes": True}


class VacancyCreate(VacancyBase):
    model_config = {"from_attributes": True}


class VacancyUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    company_id: Optional[UUID] = None
    location: Optional[str] = Field(None, max_length=255)
    employment_type: Optional[EmploymentType] = Field(None)
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None

    model_config = {"from_attributes": True}


class VacancyOut(VacancyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
