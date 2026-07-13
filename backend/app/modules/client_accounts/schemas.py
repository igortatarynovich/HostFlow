from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ClientAccountStatus = Literal["prospect", "active", "inactive"]


class ClientAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    own_company_id: Optional[str] = None
    display_name: str
    status: ClientAccountStatus
    owner_user_id: Optional[str] = None
    primary_contact_id: Optional[str] = None
    primary_company_id: Optional[str] = None
    source_lead_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClientAccountListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ClientAccountOut]
    total: int


class ClientAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=255)
    status: ClientAccountStatus = "prospect"
    owner_user_id: Optional[UUID] = None
    primary_company_id: Optional[str] = None
    source_lead_id: Optional[str] = None
    own_company_id: Optional[str] = None


class ClientAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    status: Optional[ClientAccountStatus] = None
    owner_user_id: Optional[UUID] = None
    primary_company_id: Optional[str] = None


class ClientConversionResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_account_id: str
    company_id: Optional[str] = None
    idempotent_replay: bool = False
