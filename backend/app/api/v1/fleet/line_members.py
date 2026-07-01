"""Fleet operating line ↔ vehicles / drivers membership."""

from __future__ import annotations

from datetime import date
from typing import Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.fleet_driver import FleetDriver
from backend.app.models.fleet_operating_line import FleetOperatingLine
from backend.app.models.fleet_operating_line_driver import FleetOperatingLineDriver
from backend.app.models.fleet_operating_line_vehicle import FleetOperatingLineVehicle
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.fleet_work_model import FleetWorkModel

router = APIRouter(tags=["fleet-line-members"])


async def _line_for_tenant(db: AsyncSession, tenant_id: str, line_id: str) -> FleetOperatingLine | None:
    res = await db.execute(
        select(FleetOperatingLine).where(
            FleetOperatingLine.id == line_id,
            FleetOperatingLine.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


async def _vehicle_for_tenant(db: AsyncSession, tenant_id: str, vehicle_id: str) -> FleetVehicle | None:
    res = await db.execute(
        select(FleetVehicle).where(FleetVehicle.id == vehicle_id, FleetVehicle.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def _driver_for_tenant(db: AsyncSession, tenant_id: str, driver_id: str) -> FleetDriver | None:
    res = await db.execute(
        select(FleetDriver).where(FleetDriver.id == driver_id, FleetDriver.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def _wm_for_tenant(db: AsyncSession, tenant_id: str, wm_id: str) -> FleetWorkModel | None:
    res = await db.execute(
        select(FleetWorkModel).where(FleetWorkModel.id == wm_id, FleetWorkModel.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


def _vehicle_label(v: FleetVehicle) -> str:
    return v.internal_code or v.registration_plate or " ".join(filter(None, [v.brand, v.model])) or v.id[:8]


def _driver_label(d: FleetDriver) -> str:
    return d.display_code or " ".join(filter(None, [d.first_name, d.last_name])) or d.id[:8]


# --- Line vehicles ------------------------------------------------------------

class LineVehicleOut(BaseModel):
    id: str
    line_id: str
    vehicle_id: str
    default_work_model_id: str | None = None
    vehicle_label: str


class LineVehiclesListOut(BaseModel):
    items: list[LineVehicleOut]


class LineVehicleCreateIn(BaseModel):
    vehicle_id: str = Field(..., min_length=1, max_length=36)
    default_work_model_id: str | None = Field(None, max_length=36)


class LineVehiclePatchIn(BaseModel):
    default_work_model_id: str | None = Field(default=None, max_length=36)


async def _olv_for_tenant(db: AsyncSession, tenant_id: str, line_id: str, m_id: str) -> FleetOperatingLineVehicle | None:
    res = await db.execute(
        select(FleetOperatingLineVehicle).where(
            FleetOperatingLineVehicle.id == m_id,
            FleetOperatingLineVehicle.line_id == line_id,
            FleetOperatingLineVehicle.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


@router.get("/operating-lines/{line_id}/vehicles", response_model=LineVehiclesListOut)
async def list_line_vehicles(
    line_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LineVehiclesListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _line_for_tenant(db, tenant_id, line_id) is None:
        raise HTTPException(status_code=404, detail="operating line not found")
    res = await db.execute(
        select(FleetOperatingLineVehicle).where(
            FleetOperatingLineVehicle.line_id == line_id,
            FleetOperatingLineVehicle.tenant_id == tenant_id,
        )
    )
    rows = list(res.scalars().all())
    out: list[LineVehicleOut] = []
    for m in rows:
        v = await _vehicle_for_tenant(db, tenant_id, m.vehicle_id)
        label = _vehicle_label(v) if v else m.vehicle_id[:8]
        out.append(
            LineVehicleOut(
                id=m.id,
                line_id=m.line_id,
                vehicle_id=m.vehicle_id,
                default_work_model_id=m.default_work_model_id,
                vehicle_label=label,
            )
        )
    return LineVehiclesListOut(items=out)


@router.post("/operating-lines/{line_id}/vehicles", response_model=LineVehicleOut, status_code=status.HTTP_201_CREATED)
async def add_line_vehicle(
    line_id: str,
    body: LineVehicleCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LineVehicleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _line_for_tenant(db, tenant_id, line_id) is None:
        raise HTTPException(status_code=404, detail="operating line not found")
    v = await _vehicle_for_tenant(db, tenant_id, body.vehicle_id)
    if v is None:
        raise HTTPException(status_code=400, detail="vehicle not found in tenant")
    if body.default_work_model_id and await _wm_for_tenant(db, tenant_id, body.default_work_model_id) is None:
        raise HTTPException(status_code=400, detail="default_work_model_id not found in tenant")
    row = FleetOperatingLineVehicle(
        id=str(uuid4()),
        tenant_id=tenant_id,
        line_id=line_id,
        vehicle_id=body.vehicle_id,
        default_work_model_id=body.default_work_model_id,
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="vehicle already on this line") from exc
    return LineVehicleOut(
        id=row.id,
        line_id=row.line_id,
        vehicle_id=row.vehicle_id,
        default_work_model_id=row.default_work_model_id,
        vehicle_label=_vehicle_label(v),
    )


@router.patch("/operating-lines/{line_id}/vehicles/{membership_id}", response_model=LineVehicleOut)
async def patch_line_vehicle(
    line_id: str,
    membership_id: str,
    body: LineVehiclePatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LineVehicleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    m = await _olv_for_tenant(db, tenant_id, line_id, membership_id)
    if m is None:
        raise HTTPException(status_code=404, detail="membership not found")
    data = body.model_dump(exclude_unset=True)
    if "default_work_model_id" in data:
        val = data["default_work_model_id"]
        if val and await _wm_for_tenant(db, tenant_id, str(val)) is None:
            raise HTTPException(status_code=400, detail="default_work_model_id not found in tenant")
        m.default_work_model_id = val
    await db.commit()
    await db.refresh(m)
    v = await _vehicle_for_tenant(db, tenant_id, m.vehicle_id)
    label = _vehicle_label(v) if v else m.vehicle_id[:8]
    return LineVehicleOut(
        id=m.id,
        line_id=m.line_id,
        vehicle_id=m.vehicle_id,
        default_work_model_id=m.default_work_model_id,
        vehicle_label=label,
    )


@router.delete("/operating-lines/{line_id}/vehicles/{membership_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_line_vehicle(
    line_id: str,
    membership_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _olv_for_tenant(db, tenant_id, line_id, membership_id) is None:
        raise HTTPException(status_code=404, detail="membership not found")
    await db.execute(
        sql_delete(FleetOperatingLineVehicle).where(
            FleetOperatingLineVehicle.id == membership_id,
            FleetOperatingLineVehicle.line_id == line_id,
            FleetOperatingLineVehicle.tenant_id == tenant_id,
        )
    )
    await db.commit()


# --- Line drivers -------------------------------------------------------------

class LineDriverOut(BaseModel):
    id: str
    line_id: str
    fleet_driver_id: str
    work_model_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    driver_label: str


class LineDriversListOut(BaseModel):
    items: list[LineDriverOut]


class LineDriverCreateIn(BaseModel):
    fleet_driver_id: str = Field(..., min_length=1, max_length=36)
    work_model_id: str = Field(..., min_length=1, max_length=36)
    effective_from: date | None = None
    effective_to: date | None = None


class LineDriverPatchIn(BaseModel):
    work_model_id: str | None = Field(None, min_length=1, max_length=36)
    effective_from: date | None = None
    effective_to: date | None = None


async def _old_for_tenant(db: AsyncSession, tenant_id: str, line_id: str, m_id: str) -> FleetOperatingLineDriver | None:
    res = await db.execute(
        select(FleetOperatingLineDriver).where(
            FleetOperatingLineDriver.id == m_id,
            FleetOperatingLineDriver.line_id == line_id,
            FleetOperatingLineDriver.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


@router.get("/operating-lines/{line_id}/drivers", response_model=LineDriversListOut)
async def list_line_drivers(
    line_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LineDriversListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _line_for_tenant(db, tenant_id, line_id) is None:
        raise HTTPException(status_code=404, detail="operating line not found")
    res = await db.execute(
        select(FleetOperatingLineDriver).where(
            FleetOperatingLineDriver.line_id == line_id,
            FleetOperatingLineDriver.tenant_id == tenant_id,
        )
    )
    rows = list(res.scalars().all())
    out: list[LineDriverOut] = []
    for m in rows:
        d = await _driver_for_tenant(db, tenant_id, m.fleet_driver_id)
        label = _driver_label(d) if d else m.fleet_driver_id[:8]
        out.append(
            LineDriverOut(
                id=m.id,
                line_id=m.line_id,
                fleet_driver_id=m.fleet_driver_id,
                work_model_id=m.work_model_id,
                effective_from=m.effective_from,
                effective_to=m.effective_to,
                driver_label=label,
            )
        )
    return LineDriversListOut(items=out)


@router.post("/operating-lines/{line_id}/drivers", response_model=LineDriverOut, status_code=status.HTTP_201_CREATED)
async def add_line_driver(
    line_id: str,
    body: LineDriverCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LineDriverOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _line_for_tenant(db, tenant_id, line_id) is None:
        raise HTTPException(status_code=404, detail="operating line not found")
    d = await _driver_for_tenant(db, tenant_id, body.fleet_driver_id)
    if d is None:
        raise HTTPException(status_code=400, detail="driver not found in tenant")
    if await _wm_for_tenant(db, tenant_id, body.work_model_id) is None:
        raise HTTPException(status_code=400, detail="work_model_id not found in tenant")
    row = FleetOperatingLineDriver(
        id=str(uuid4()),
        tenant_id=tenant_id,
        line_id=line_id,
        fleet_driver_id=body.fleet_driver_id,
        work_model_id=body.work_model_id,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="driver already on this line") from exc
    return LineDriverOut(
        id=row.id,
        line_id=row.line_id,
        fleet_driver_id=row.fleet_driver_id,
        work_model_id=row.work_model_id,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        driver_label=_driver_label(d),
    )


@router.patch("/operating-lines/{line_id}/drivers/{membership_id}", response_model=LineDriverOut)
async def patch_line_driver(
    line_id: str,
    membership_id: str,
    body: LineDriverPatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> LineDriverOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    m = await _old_for_tenant(db, tenant_id, line_id, membership_id)
    if m is None:
        raise HTTPException(status_code=404, detail="membership not found")
    data = body.model_dump(exclude_unset=True)
    if "work_model_id" in data and data["work_model_id"]:
        if await _wm_for_tenant(db, tenant_id, str(data["work_model_id"])) is None:
            raise HTTPException(status_code=400, detail="work_model_id not found in tenant")
    for key, value in data.items():
        setattr(m, key, value)
    await db.commit()
    await db.refresh(m)
    d = await _driver_for_tenant(db, tenant_id, m.fleet_driver_id)
    label = _driver_label(d) if d else m.fleet_driver_id[:8]
    return LineDriverOut(
        id=m.id,
        line_id=m.line_id,
        fleet_driver_id=m.fleet_driver_id,
        work_model_id=m.work_model_id,
        effective_from=m.effective_from,
        effective_to=m.effective_to,
        driver_label=label,
    )


@router.delete("/operating-lines/{line_id}/drivers/{membership_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_line_driver(
    line_id: str,
    membership_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _old_for_tenant(db, tenant_id, line_id, membership_id) is None:
        raise HTTPException(status_code=404, detail="membership not found")
    await db.execute(
        sql_delete(FleetOperatingLineDriver).where(
            FleetOperatingLineDriver.id == membership_id,
            FleetOperatingLineDriver.line_id == line_id,
            FleetOperatingLineDriver.tenant_id == tenant_id,
        )
    )
    await db.commit()
