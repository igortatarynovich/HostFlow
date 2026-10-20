"""Settings: connect a TikTok ad account and expose its Instant Forms as flight sources."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_own_company_id_for_session
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.leads.tiktok_connection import (
    TikTokConnectionError,
    connect_tiktok_account,
    connection_status,
    disconnect_tiktok_account,
    import_tiktok_leads,
)

router = APIRouter(prefix="/tiktok", tags=["settings-tiktok-leads"])


class TikTokFormOut(BaseModel):
    page_id: str
    name: str
    intake_source_profile_id: str


class TikTokConnectionOut(BaseModel):
    connected: bool
    status: str
    advertiser_id: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    last_error: Optional[str] = None
    forms: list[TikTokFormOut] = Field(default_factory=list)
    imported: Optional[int] = None


class TikTokConnectIn(BaseModel):
    advertiser_id: str = Field(min_length=1, max_length=64)
    access_token: str = Field(min_length=8, max_length=4096)


def _http_error(exc: TikTokConnectionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)


async def _company(
    db: AsyncSession,
    tenant_id: str,
    ctx: UserCtx,
    header: Optional[str],
) -> str:
    return await resolve_own_company_id_for_session(db, tenant_id, ctx, header)


@router.get("", response_model=TikTokConnectionOut, dependencies=[Depends(require_trust_read())])
async def get_tiktok_connection(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
) -> TikTokConnectionOut:
    db, tenant_uuid = db_tenant
    company_id = await _company(db, str(tenant_uuid), ctx, x_own_company_id)
    payload = await connection_status(db, tenant_id=str(tenant_uuid), own_company_id=company_id)
    return TikTokConnectionOut.model_validate(payload)


@router.post("/connect", response_model=TikTokConnectionOut, dependencies=[Depends(require_trust_admin())])
async def post_tiktok_connect(
    body: TikTokConnectIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
) -> TikTokConnectionOut:
    db, tenant_uuid = db_tenant
    company_id = await _company(db, str(tenant_uuid), ctx, x_own_company_id)
    try:
        payload = await connect_tiktok_account(
            db,
            tenant_id=str(tenant_uuid),
            own_company_id=company_id,
            advertiser_id=body.advertiser_id,
            access_token=body.access_token,
        )
    except TikTokConnectionError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return TikTokConnectionOut.model_validate(payload)


@router.post("/import", response_model=TikTokConnectionOut, dependencies=[Depends(require_trust_admin())])
async def post_tiktok_import(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
) -> TikTokConnectionOut:
    db, tenant_uuid = db_tenant
    company_id = await _company(db, str(tenant_uuid), ctx, x_own_company_id)
    try:
        payload = await import_tiktok_leads(
            db,
            tenant_id=str(tenant_uuid),
            own_company_id=company_id,
        )
    except TikTokConnectionError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return TikTokConnectionOut.model_validate(payload)


@router.delete("/connect", response_model=TikTokConnectionOut, dependencies=[Depends(require_trust_admin())])
async def delete_tiktok_connect(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
) -> TikTokConnectionOut:
    db, tenant_uuid = db_tenant
    company_id = await _company(db, str(tenant_uuid), ctx, x_own_company_id)
    payload = await disconnect_tiktok_account(
        db,
        tenant_id=str(tenant_uuid),
        own_company_id=company_id,
    )
    await db.commit()
    return TikTokConnectionOut.model_validate(payload)
