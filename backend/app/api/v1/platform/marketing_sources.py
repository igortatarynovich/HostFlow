"""Marketing Sources API — C-3 list + C-4 sample + C-5 mapping façade."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.sources_mapping import (
    get_source_mapping,
    preview_source_routing,
    put_source_mapping,
)
from backend.app.acquisition.sources_read import list_marketing_source_summaries
from backend.app.acquisition.sources_sample import (
    arm_capture_next,
    get_source_sample,
    preview_source_sample,
    store_sample_from_payload,
)
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role
from backend.app.db.deps import get_db_with_tenant

router = APIRouter(
    prefix="/platform/marketing/sources",
    tags=["marketing-sources"],
    redirect_slashes=False,
)

_READ = [
    Depends(
        require_trust_read()
    )
]

_WRITE = [
    Depends(
        require_trust_write()
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


class SourceMappingOut(BaseModel):
    source_id: str
    provider: str
    display_name: str
    meta_form_id: Optional[str] = None
    mapping_rules: list[dict[str, Any]] = Field(default_factory=list)
    profile_mapping_rules: list[dict[str, Any]] = Field(default_factory=list)
    rules_source: str = "none"
    mapping_rules_count: int = 0
    mapping_health: str
    destination: Optional[str] = None
    destination_label: Optional[str] = None
    route_intent: Optional[str] = None
    schema_source: str = "none"
    has_schema: bool = False
    has_sample: bool = False
    schema_fields: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    contract_health: Optional[str] = None
    destinations: list[dict[str, Any]] = Field(default_factory=list)
    projection: list[dict[str, Any]] = Field(default_factory=list)


class SourceMappingPutIn(BaseModel):
    mapping_rules: list[dict[str, Any]] = Field(default_factory=list)
    schema_snapshot: Optional[dict[str, Any]] = None


class SourceRoutingPreviewIn(BaseModel):
    sample_payload: Optional[dict[str, Any]] = None


class SourceRoutingPreviewOut(BaseModel):
    source_id: str
    creates_entities: bool = False
    destination: Optional[str] = None
    destination_label: Optional[str] = None
    route_intent: Optional[str] = None
    mapping_health: Optional[str] = None
    mapping_rules_count: Optional[int] = None
    unmapped_fields: list[str] = Field(default_factory=list)
    ignored_fields: list[str] = Field(default_factory=list)
    needs_review: bool = False
    preview: dict[str, Any] = Field(default_factory=dict)
    note: str = ""


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


@router.get(
    "/{source_id}/mapping",
    response_model=SourceMappingOut,
    dependencies=_READ,
)
async def get_marketing_source_mapping(
    source_id: str,
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> SourceMappingOut:
    db, tenant_id = db_tenant
    result = await get_source_mapping(db, tenant_id=str(tenant_id), source_id=str(source_id))
    return SourceMappingOut.model_validate(result)


@router.put(
    "/{source_id}/mapping",
    response_model=SourceMappingOut,
    dependencies=_WRITE,
)
async def put_marketing_source_mapping(
    source_id: str,
    payload: SourceMappingPutIn,
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> SourceMappingOut:
    db, tenant_id = db_tenant
    result = await put_source_mapping(
        db,
        tenant_id=str(tenant_id),
        source_id=str(source_id),
        mapping_rules=payload.mapping_rules,
        schema_snapshot=payload.schema_snapshot,
    )
    return SourceMappingOut.model_validate(result)


@router.post(
    "/{source_id}/mapping/routing-preview",
    response_model=SourceRoutingPreviewOut,
    dependencies=_WRITE,
)
async def post_marketing_source_routing_preview(
    source_id: str,
    payload: SourceRoutingPreviewIn,
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> SourceRoutingPreviewOut:
    db, tenant_id = db_tenant
    result = await preview_source_routing(
        db,
        tenant_id=str(tenant_id),
        source_id=str(source_id),
        sample_payload=payload.sample_payload,
    )
    return SourceRoutingPreviewOut.model_validate(result)
