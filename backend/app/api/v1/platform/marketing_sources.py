"""Marketing Sources API — Acquisition UI Cutover C-3 list + C-4 sample façade."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.sources_read import list_marketing_source_summaries
from backend.app.acquisition.sources_sample import (
    arm_capture_next,
    get_source_sample,
    preview_source_sample,
    store_sample_from_payload,
)
from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant

router = APIRouter(
    prefix="/platform/marketing/sources",
    tags=["marketing-sources"],
    redirect_slashes=False,
)

_READ = [
    Depends(
        require_roles(
            Role.administrator,
            Role.supervisor,
            Role.recruiter,
            Role.client_manager,
            Role.viewer,
            Role.hr_officer,
            Role.superadmin,
        )
    )
]

_WRITE = [
    Depends(
        require_roles(
            Role.administrator,
            Role.supervisor,
            Role.superadmin,
        )
    )
]


class MarketingSourceSummaryOut(BaseModel):
    source_id: str
    provider: str
    display_name: str
    connection_status: str
    mapping_health: str
    last_submission_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_code: Optional[str] = None
    campaign_count: int = 0
    flight_count: int = 0
    mapping_path: str
    test_lead_path: str
    settings_path: str
    code: str = ""
    is_active: bool = True
    mapping_rules_count: int = 0
    active_binding_count: int = 0
    waiting_submissions: int = 0
    last_problematic_ad_id: Optional[str] = None
    routing_issue_code: Optional[str] = None
    routing_issue_message: Optional[str] = None
    setup_campaign_flight_path: Optional[str] = None
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    provider_form: Optional[str] = None
    destination: Optional[str] = None
    destination_label: Optional[str] = None


class MarketingSourceListOut(BaseModel):
    items: list[MarketingSourceSummaryOut] = Field(default_factory=list)


class DiscoveredFieldOut(BaseModel):
    source: str
    sample_value_masked: str
    proposed_target: Optional[str] = None
    status: str


class SourceSampleOut(BaseModel):
    source_id: str
    sample_source: str
    lead_id: Optional[str] = None
    captured_at: Optional[str] = None
    capture_next_until: Optional[str] = None
    has_sample: bool = False
    fields: list[DiscoveredFieldOut] = Field(default_factory=list)
    raw_payload_masked: dict[str, Any] = Field(default_factory=dict)
    mapping_rules_count: int = 0


class SourceSamplePayloadIn(BaseModel):
    sample_payload: dict[str, Any] = Field(default_factory=dict)


class SourceSamplePreviewIn(BaseModel):
    sample_payload: Optional[dict[str, Any]] = None


class SourceSamplePreviewOut(BaseModel):
    source_id: str
    fields: list[DiscoveredFieldOut] = Field(default_factory=list)
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    raw_payload_masked: dict[str, Any] = Field(default_factory=dict)
    mapping_rules_count: int = 0
    accepted_rules: list[dict[str, Any]] = Field(default_factory=list)
    creates_entities: bool = False


class CaptureNextOut(BaseModel):
    source_id: str
    capture_next_armed_at: str
    capture_next_until: str
    message: str


@router.get("", response_model=MarketingSourceListOut, dependencies=_READ)
async def list_marketing_sources(
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> MarketingSourceListOut:
    db, tenant_id = db_tenant
    rows = await list_marketing_source_summaries(db, tenant_id=str(tenant_id))
    return MarketingSourceListOut(
        items=[MarketingSourceSummaryOut(**row.as_dict()) for row in rows]
    )


@router.get(
    "/{source_id}/sample",
    response_model=SourceSampleOut,
    dependencies=_READ,
)
async def get_marketing_source_sample(
    source_id: str,
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> SourceSampleOut:
    db, tenant_id = db_tenant
    result = await get_source_sample(db, tenant_id=str(tenant_id), source_id=str(source_id))
    return SourceSampleOut.model_validate(result)


@router.post(
    "/{source_id}/sample/from-payload",
    response_model=SourceSampleOut,
    dependencies=_WRITE,
)
async def post_marketing_source_sample_from_payload(
    source_id: str,
    payload: SourceSamplePayloadIn,
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> SourceSampleOut:
    db, tenant_id = db_tenant
    result = await store_sample_from_payload(
        db,
        tenant_id=str(tenant_id),
        source_id=str(source_id),
        sample_payload=payload.sample_payload,
    )
    return SourceSampleOut.model_validate(result)


@router.post(
    "/{source_id}/sample/capture-next",
    response_model=CaptureNextOut,
    dependencies=_WRITE,
)
async def post_marketing_source_capture_next(
    source_id: str,
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> CaptureNextOut:
    db, tenant_id = db_tenant
    result = await arm_capture_next(db, tenant_id=str(tenant_id), source_id=str(source_id))
    return CaptureNextOut.model_validate(result)


@router.post(
    "/{source_id}/sample/preview",
    response_model=SourceSamplePreviewOut,
    dependencies=_WRITE,
)
async def post_marketing_source_sample_preview(
    source_id: str,
    payload: SourceSamplePreviewIn,
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> SourceSamplePreviewOut:
    db, tenant_id = db_tenant
    result = await preview_source_sample(
        db,
        tenant_id=str(tenant_id),
        source_id=str(source_id),
        sample_payload=payload.sample_payload,
    )
    return SourceSamplePreviewOut.model_validate(result)
