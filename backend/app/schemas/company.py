from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, AnyUrl, ConfigDict, Field


class CompanyBase(BaseModel):
    title: Optional[str] = None
    short_name: Optional[str]
    legal_name: Optional[str]

    country_code: Optional[str]
    city: Optional[str]
    address: Optional[str]

    phone: Optional[str]
    phone_country_code: Optional[str]
    email: Optional[EmailStr]
    website: Optional[AnyUrl]

    tax_id: Optional[str]
    reg_number: Optional[str]

    note: Optional[str]
    extra: Optional[dict[str, Any]]


class CompanyCreate(CompanyBase):
    title: str = Field(...)  # pyright: ignore[reportGeneralTypeIssues]
    model_config = ConfigDict(from_attributes=True)


class CompanyUpdate(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = None
    short_name: Optional[str] = None
    legal_name: Optional[str] = None

    country_code: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None

    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[AnyUrl] = None

    tax_id: Optional[str] = None
    reg_number: Optional[str] = None

    note: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[UUID]
    short_id: Optional[str]

    title: str
    short_name: Optional[str]
    legal_name: Optional[str]

    country_code: Optional[str]
    city: Optional[str]
    address: Optional[str]

    phone: Optional[str]
    phone_country_code: Optional[str]
    email: Optional[EmailStr]
    website: Optional[AnyUrl]

    tax_id: Optional[str]
    reg_number: Optional[str]

    note: Optional[str]
    extra: Optional[dict[str, Any]]

    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]