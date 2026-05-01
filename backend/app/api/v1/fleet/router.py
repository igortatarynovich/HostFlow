from __future__ import annotations

from typing import Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.company import Company
from backend.app.models.fleet_operating_line import FleetOperatingLine

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
    status: str = "active"
    operating_company_id: str | None = None
    client_company_id: str | None = None
    seasonality_month_factors: list[float] | None = None


class OperatingLinesListOut(BaseModel):
    items: list[OperatingLineOut]


class OperatingLineCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    status: str = Field(default="active", max_length=32)
    operating_company_id: str | None = None
    client_company_id: str | None = None


class OperatingLinePatchIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(None, max_length=32)
    operating_company_id: str | None = None
    client_company_id: str | None = None
    seasonality_month_factors: list[float] | None = None


def _out_from_row(r: FleetOperatingLine) -> OperatingLineOut:
    raw = r.seasonality_month_factors
    factors: list[float] | None = None
    if raw is not None and isinstance(raw, list):
        try:
            factors = [float(x) for x in raw]
        except (TypeError, ValueError):
            factors = None
    return OperatingLineOut(
        id=r.id,
        name=r.name,
        status=r.status,
        operating_company_id=r.operating_company_id,
        client_company_id=r.client_company_id,
        seasonality_month_factors=factors,
    )


def _validate_seasonality(factors: list[float] | None) -> None:
    if factors is None:
        return
    if len(factors) != 12:
        raise HTTPException(status_code=400, detail="seasonality_month_factors must have exactly 12 entries")
    for i, v in enumerate(factors):
        if v < 0.01 or v > 10.0:
            raise HTTPException(
                status_code=400,
                detail=f"seasonality_month_factors[{i}] must be between 0.01 and 10",
            )


async def _line_for_tenant(db: AsyncSession, tenant_id: str, line_id: str) -> FleetOperatingLine | None:
    res = await db.execute(
        select(FleetOperatingLine).where(
            FleetOperatingLine.id == line_id,
            FleetOperatingLine.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


async def _company_in_tenant(db: AsyncSession, tenant_id: str, company_id: str) -> bool:
    res = await db.execute(
        select(Company.id).where(Company.id == company_id, Company.tenant_id == tenant_id).limit(1)
    )
    return res.scalar_one_or_none() is not None


@router.get("/operating-lines", response_model=OperatingLinesListOut)
async def list_operating_lines(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> OperatingLinesListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    res = await db.execute(
        select(FleetOperatingLine)
        .where(FleetOperatingLine.tenant_id == tenant_id)
        .order_by(FleetOperatingLine.name.asc())
    )
    rows = res.scalars().all()
    return OperatingLinesListOut(items=[_out_from_row(r) for r in rows])


@router.post("/operating-lines", response_model=OperatingLineOut, status_code=status.HTTP_201_CREATED)
async def create_operating_line(
    body: OperatingLineCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> OperatingLineOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)

    if body.operating_company_id and not await _company_in_tenant(db, tenant_id, body.operating_company_id):
        raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    if body.client_company_id and not await _company_in_tenant(db, tenant_id, body.client_company_id):
        raise HTTPException(status_code=400, detail="client_company_id not found in tenant")

    row = FleetOperatingLine(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name=body.name.strip(),
        status=(body.status or "active").strip() or "active",
        operating_company_id=body.operating_company_id,
        client_company_id=body.client_company_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _out_from_row(row)


@router.get("/operating-lines/{line_id}", response_model=OperatingLineOut)
async def get_operating_line(
    line_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> OperatingLineOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _line_for_tenant(db, tenant_id, line_id)
    if row is None:
        raise HTTPException(status_code=404, detail="operating line not found")
    return _out_from_row(row)


@router.patch("/operating-lines/{line_id}", response_model=OperatingLineOut)
async def patch_operating_line(
    line_id: str,
    body: OperatingLinePatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> OperatingLineOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _line_for_tenant(db, tenant_id, line_id)
    if row is None:
        raise HTTPException(status_code=404, detail="operating line not found")

    data = body.model_dump(exclude_unset=True)
    if "seasonality_month_factors" in data:
        _validate_seasonality(data["seasonality_month_factors"])
    if "operating_company_id" in data and data["operating_company_id"]:
        if not await _company_in_tenant(db, tenant_id, str(data["operating_company_id"])):
            raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    if "client_company_id" in data and data["client_company_id"]:
        if not await _company_in_tenant(db, tenant_id, str(data["client_company_id"])):
            raise HTTPException(status_code=400, detail="client_company_id not found in tenant")

    for key, value in data.items():
        if key == "name" and value is not None:
            setattr(row, key, str(value).strip())
        elif key == "status" and value is not None:
            setattr(row, key, str(value).strip() or "active")
        elif key in ("operating_company_id", "client_company_id", "seasonality_month_factors"):
            setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return _out_from_row(row)


@router.delete("/operating-lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operating_line(
    line_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _line_for_tenant(db, tenant_id, line_id)
    if row is None:
        raise HTTPException(status_code=404, detail="operating line not found")
    await db.execute(sql_delete(FleetOperatingLine).where(FleetOperatingLine.id == line_id, FleetOperatingLine.tenant_id == tenant_id))
    await db.commit()


from backend.app.api.v1.fleet.park import router as fleet_park_router  # noqa: E402

router.include_router(fleet_park_router)
