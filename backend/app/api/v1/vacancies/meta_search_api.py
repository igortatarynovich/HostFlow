from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id
from backend.app.services.meta_search_binding_service import (
    bind_meta_campaigns_to_search,
    build_meta_search_inventory,
)

router = APIRouter(tags=["vacancies-meta-search"])


class MetaSearchCampaignOut(BaseModel):
    id: str
    name: str
    status: str = ""
    objective: str = ""
    ads_count: int = 0
    bound_to_search: bool = False


class MetaSearchInventoryOut(BaseModel):
    connected: bool = False
    needs_marketing_reconnect: bool = False
    page_id: str | None = None
    ad_account_id: str | None = None
    page_name: str | None = None
    ad_account_name: str | None = None
    campaigns: list[MetaSearchCampaignOut] = Field(default_factory=list)
    bound_campaign_ids: list[str] = Field(default_factory=list)
    empty_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class MetaSearchBindCampaignsIn(BaseModel):
    campaign_ids: list[str] = Field(min_length=1, max_length=50)


class MetaSearchBindCampaignsOut(BaseModel):
    bound_ads: int = 0
    bound_forms: int = 0
    skipped: list[str] = Field(default_factory=list)
    inventory: MetaSearchInventoryOut


@router.get("/{vacancy_id}/meta/inventory", response_model=MetaSearchInventoryOut)
async def get_search_meta_inventory(
    vacancy_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    try:
        payload = await build_meta_search_inventory(db, str(tenant_id), str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return MetaSearchInventoryOut.model_validate(payload)


@router.post(
    "/{vacancy_id}/meta/bind-campaigns",
    response_model=MetaSearchBindCampaignsOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def bind_search_meta_campaigns(
    vacancy_id: UUID,
    payload: MetaSearchBindCampaignsIn,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    try:
        result = await bind_meta_campaigns_to_search(
            db,
            str(tenant_id),
            str(vacancy_id),
            campaign_ids=[str(x).strip() for x in payload.campaign_ids if str(x).strip()],
            user_sub=user.sub,
        )
    except LookupError as exc:
        code = str(exc)
        if code == "meta_not_connected":
            raise HTTPException(status_code=400, detail="Meta is not connected for this workspace")
        if code == "meta_marketing_reconnect_required":
            raise HTTPException(
                status_code=400,
                detail="Meta marketing access requires reconnect — sign in through Facebook again",
            )
        if code == "vacancy_missing_company":
            raise HTTPException(status_code=422, detail="Vacancy has no company context for lead routing")
        raise HTTPException(status_code=404, detail="Vacancy not found")
    await db.commit()
    return MetaSearchBindCampaignsOut.model_validate(result)
