from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ClientAccountStatus = Literal["prospect", "active", "inactive"]
DuplicateDecisionAction = Literal["open_existing", "create_new", "cancel"]


class CommercialDefaults(BaseModel):
    """Client Account commercial defaults (ADR-032 §2.4). Prefill only — not order SoT."""

    model_config = ConfigDict(extra="forbid")

    currency: Optional[str] = Field(default=None, max_length=16)
    payment_term_days: Optional[int] = Field(default=None, ge=0, le=365)
    payment_model: Optional[str] = Field(default=None, max_length=64)
    vat_rate: Optional[Decimal] = None
    guarantee_days: Optional[int] = Field(default=None, ge=0, le=3650)
    invoice_right_policy: Optional[str] = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def _currency_upper(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = str(v).strip().upper()
        return text or None


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
    commercial_defaults: Optional[dict[str, Any]] = None
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
    commercial_defaults: Optional[CommercialDefaults] = None
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
    commercial_defaults: Optional[CommercialDefaults] = None


class ClientConversionResultOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_account_id: str
    company_id: Optional[str] = None
    idempotent_replay: bool = False
