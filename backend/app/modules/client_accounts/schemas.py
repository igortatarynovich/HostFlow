from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ClientAccountStatus = Literal["prospect", "active", "inactive"]
DuplicateDecisionAction = Literal["open_existing", "create_new", "cancel"]


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
    origin_type: Optional[str] = None
    creation_ref: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClientAccountListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ClientAccountOut]
    total: int


class ClientAccountDuplicateDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: DuplicateDecisionAction
    client_account_id: Optional[str] = None


class ClientAccountCreate(BaseModel):
    """Manual ClientAccount create body (Origins v1 → create_client_account_manually).

    ``source_lead_id`` is rejected — conversion uses Sales convert mapping, not this path.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=255)
    status: ClientAccountStatus = "prospect"
    owner_user_id: Optional[UUID] = None
    primary_company_id: Optional[str] = None
    own_company_id: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    reason: Optional[str] = Field(default=None, max_length=500)
    source_note: Optional[str] = Field(default=None, max_length=500)
    force_create: bool = False
    duplicate_decision: Optional[ClientAccountDuplicateDecisionIn] = None
    # Legacy field — accepted only to fail closed with a clear error.
    source_lead_id: Optional[str] = None

    @model_validator(mode="after")
    def _reject_source_lead(self) -> ClientAccountCreate:
        if self.source_lead_id:
            raise ValueError(
                "source_lead_id is forbidden on manual create; use SalesInquiry convert mapping"
            )
        return self


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
