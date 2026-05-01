from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db_with_tenant

router = APIRouter(prefix="/fleet", tags=["fleet"], redirect_slashes=False)


class FleetStatusOut(BaseModel):
    ok: bool = True
    module: str = "fleet"


@router.get("/status", response_model=FleetStatusOut)
async def fleet_status(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> FleetStatusOut:
    db, tenant_uuid = db_tenant
    await ensure_user_can_access_tenant(db, ctx, str(tenant_uuid))
    return FleetStatusOut()


class OperatingLineOut(BaseModel):
    id: str
    name: str


class OperatingLinesListOut(BaseModel):
    items: list[OperatingLineOut]


@router.get("/operating-lines", response_model=OperatingLinesListOut)
async def list_operating_lines(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> OperatingLinesListOut:
    db, tenant_uuid = db_tenant
    await ensure_user_can_access_tenant(db, ctx, str(tenant_uuid))
    # Persistence layer lands in a follow-up; empty list keeps the contract stable.
    return OperatingLinesListOut(items=[])
