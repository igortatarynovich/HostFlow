"""Marketing Sources list API — Acquisition UI Cutover C-3 (read-only)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.sources_read import list_marketing_source_summaries
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


class MarketingSourceListOut(BaseModel):
    items: list[MarketingSourceSummaryOut] = Field(default_factory=list)


@router.get("", response_model=MarketingSourceListOut, dependencies=_READ)
async def list_marketing_sources(
    db_tenant: tuple[AsyncSession, str] = Depends(get_db_with_tenant),
) -> MarketingSourceListOut:
    db, tenant_id = db_tenant
    rows = await list_marketing_source_summaries(db, tenant_id=str(tenant_id))
    return MarketingSourceListOut(
        items=[MarketingSourceSummaryOut(**row.as_dict()) for row in rows]
    )
