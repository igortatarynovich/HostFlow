from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


LeadStatus = Literal["new", "processed", "duplicated", "failed", "needs_routing"]
LeadImportStatus = Literal["pending", "running", "completed", "failed"]


class MetaLeadResponse(BaseModel):
    lead_id: UUID
    status: LeadStatus
    vacancy_id: Optional[UUID] = None
    candidate_id: Optional[UUID] = None
    recruiter_id: Optional[UUID] = None
    error: Optional[str] = None


class LeadOut(BaseModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID
    company_name: Optional[str] = None
    vacancy_id: Optional[UUID] = None
    vacancy_title: Optional[str] = None
    source: str
    ad_id: Optional[int] = None
    status: LeadStatus
    candidate_id: Optional[UUID] = None
    candidate_name: Optional[str] = None
    recruiter_id: Optional[UUID] = None
    error: Optional[str] = None
    payload: Dict[str, Any]
    normalized: Optional[Dict[str, Any]] = None
    created_at: datetime
    last_routed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: List[LeadOut]
    total: int
    limit: int
    offset: int


class LeadImportJobOut(BaseModel):
    id: UUID
    filename: str
    status: LeadImportStatus
    total_rows: int
    processed_rows: int
    success_rows: int
    duplicate_rows: int
    failed_rows: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_report: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)


class LeadImportJobListResponse(BaseModel):
    items: List[LeadImportJobOut]


MetaCredentialStatus = Literal["active", "disabled", "rotation_pending"]


class MetaCredentialCreate(BaseModel):
    label: str
    status: MetaCredentialStatus = "active"
    secret: Optional[str] = None
    access_token: Optional[str] = None
    ad_account_id: Optional[str] = None
    page_id: Optional[str] = None


class MetaCredentialUpdate(BaseModel):
    label: Optional[str] = None
    status: Optional[MetaCredentialStatus] = None
    secret: Optional[str] = None
    access_token: Optional[str] = None
    ad_account_id: Optional[str] = None
    page_id: Optional[str] = None


class MetaCredentialOut(BaseModel):
    id: UUID
    label: str
    status: MetaCredentialStatus
    has_secret: bool
    ad_account_last4: Optional[str] = None
    page_id_masked: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None
    last_rotation_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MetaCredentialRotateResponse(BaseModel):
    secret: str


class MetaLeadSettingsOut(BaseModel):
    tenant_id: UUID
    default_company_id: Optional[UUID] = None
    fallback_recruiter_id: Optional[UUID] = None
    auto_create_enabled: bool
    reroute_after_hours: Optional[int] = None
    mask_pii_in_logs: bool
    pull_field_data_from_graph: bool
    webhook_url: Optional[str] = None
    last_webhook_check_at: Optional[datetime] = None
    last_signature_status: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetaLeadSettingsUpdate(BaseModel):
    default_company_id: Optional[UUID] = None
    fallback_recruiter_id: Optional[UUID] = None
    auto_create_enabled: Optional[bool] = None
    reroute_after_hours: Optional[int] = None
    mask_pii_in_logs: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    pull_field_data_from_graph: Optional[bool] = None


class MetaAdsMapEntry(BaseModel):
    ad_id: str
    vacancy_id: UUID
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("ad_id", mode="before")
    @classmethod
    def _ensure_string(cls, value: Any) -> str:
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("ad_id must not be empty")
            return stripped
        raise TypeError("ad_id must be a string value")


class MetaAdsMapCreate(BaseModel):
    ad_id: str
    vacancy_id: UUID
    note: Optional[str] = None

    @field_validator("ad_id", mode="before")
    @classmethod
    def _normalize_ad_id(cls, value: Any) -> str:
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("ad_id must not be empty")
            if not stripped.isdigit():
                raise ValueError("ad_id must be numeric")
            return stripped
        raise TypeError("ad_id must be a string or integer")


class MetaAdsMapUpdate(BaseModel):
    vacancy_id: Optional[UUID] = None
    note: Optional[str] = None


class MetaLeadRerouteRequest(BaseModel):
    vacancy_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    force_process: bool = False


class MetaLeadRetryItem(BaseModel):
    lead_id: UUID
    status_before: LeadStatus
    status_after: LeadStatus
    candidate_id: Optional[UUID] = None
    error_before: Optional[str] = None
    error_after: Optional[str] = None
    processed: bool = False
    message: Optional[str] = None


class MetaLeadRetryRequest(BaseModel):
    lead_ids: Optional[List[UUID]] = None
    statuses: Optional[List[LeadStatus]] = None
    limit: Optional[int] = None
    refresh_graph: bool = True


class MetaLeadRetryResponse(BaseModel):
    items: List[MetaLeadRetryItem]
    processed: int
    failed: int
    skipped: int
