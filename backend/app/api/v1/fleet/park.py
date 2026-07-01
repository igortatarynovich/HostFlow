"""Fleet park: vehicles, trailers, drivers (CRUD under /fleet/*)."""

from __future__ import annotations

from typing import Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.company import Company
from backend.app.models.fleet_driver import FleetDriver
from backend.app.models.fleet_trailer import FleetTrailer
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.workforce_employee import WorkforceEmployee

router = APIRouter(tags=["fleet-park"])


async def _company_in_tenant(db: AsyncSession, tenant_id: str, company_id: str) -> bool:
    res = await db.execute(
        select(Company.id).where(Company.id == company_id, Company.tenant_id == tenant_id).limit(1)
    )
    return res.scalar_one_or_none() is not None


async def _workforce_in_tenant(db: AsyncSession, tenant_id: str, employee_id: str) -> bool:
    res = await db.execute(
        select(WorkforceEmployee.id).where(
            WorkforceEmployee.id == employee_id,
            WorkforceEmployee.tenant_id == tenant_id,
        ).limit(1)
    )
    return res.scalar_one_or_none() is not None


# --- Vehicles -----------------------------------------------------------------

class VehicleOut(BaseModel):
    id: str
    internal_code: str | None = None
    registration_plate: str | None = None
    vin: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    status: str = "active"
    operating_company_id: str | None = None
    notes: str | None = None


class VehiclesListOut(BaseModel):
    items: list[VehicleOut]


class VehicleCreateIn(BaseModel):
    internal_code: str | None = Field(None, max_length=64)
    registration_plate: str | None = Field(None, max_length=32)
    vin: str | None = Field(None, max_length=32)
    brand: str | None = Field(None, max_length=64)
    model: str | None = Field(None, max_length=64)
    year: int | None = Field(None, ge=1900, le=2100)
    status: str = Field(default="active", max_length=32)
    operating_company_id: str | None = None
    notes: str | None = None


class VehiclePatchIn(BaseModel):
    internal_code: str | None = Field(None, max_length=64)
    registration_plate: str | None = Field(None, max_length=32)
    vin: str | None = Field(None, max_length=32)
    brand: str | None = Field(None, max_length=64)
    model: str | None = Field(None, max_length=64)
    year: int | None = Field(None, ge=1900, le=2100)
    status: str | None = Field(None, max_length=32)
    operating_company_id: str | None = None
    notes: str | None = None


def _vehicle_out(r: FleetVehicle) -> VehicleOut:
    return VehicleOut(
        id=r.id,
        internal_code=r.internal_code,
        registration_plate=r.registration_plate,
        vin=r.vin,
        brand=r.brand,
        model=r.model,
        year=int(r.year) if r.year is not None else None,
        status=r.status,
        operating_company_id=r.operating_company_id,
        notes=r.notes,
    )


async def _vehicle_for_tenant(db: AsyncSession, tenant_id: str, vid: str) -> FleetVehicle | None:
    res = await db.execute(
        select(FleetVehicle).where(FleetVehicle.id == vid, FleetVehicle.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


@router.get("/vehicles", response_model=VehiclesListOut)
async def list_vehicles(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> VehiclesListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    res = await db.execute(
        select(FleetVehicle)
        .where(FleetVehicle.tenant_id == tenant_id)
        .order_by(FleetVehicle.internal_code.asc(), FleetVehicle.registration_plate.asc(), FleetVehicle.id.asc())
    )
    return VehiclesListOut(items=[_vehicle_out(r) for r in res.scalars().all()])


@router.post("/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: VehicleCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> VehicleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if body.operating_company_id and not await _company_in_tenant(db, tenant_id, body.operating_company_id):
        raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    row = FleetVehicle(
        id=str(uuid4()),
        tenant_id=tenant_id,
        internal_code=body.internal_code.strip() if body.internal_code else None,
        registration_plate=body.registration_plate.strip() if body.registration_plate else None,
        vin=body.vin.strip() if body.vin else None,
        brand=body.brand.strip() if body.brand else None,
        model=body.model.strip() if body.model else None,
        year=body.year,
        status=(body.status or "active").strip() or "active",
        operating_company_id=body.operating_company_id,
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _vehicle_out(row)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(
    vehicle_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> VehicleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _vehicle_for_tenant(db, tenant_id, vehicle_id)
    if row is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    return _vehicle_out(row)


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def patch_vehicle(
    vehicle_id: str,
    body: VehiclePatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> VehicleOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _vehicle_for_tenant(db, tenant_id, vehicle_id)
    if row is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    data = body.model_dump(exclude_unset=True)
    if "operating_company_id" in data and data["operating_company_id"]:
        if not await _company_in_tenant(db, tenant_id, str(data["operating_company_id"])):
            raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    for key, value in data.items():
        if key in ("internal_code", "registration_plate", "vin", "brand", "model", "notes") and value is not None:
            setattr(row, key, str(value).strip() if isinstance(value, str) else value)
        elif key == "year":
            setattr(row, "year", value)
        elif key == "status" and value is not None:
            setattr(row, key, str(value).strip() or "active")
        elif key == "operating_company_id":
            setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return _vehicle_out(row)


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_vehicle(
    vehicle_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _vehicle_for_tenant(db, tenant_id, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    await db.execute(sql_delete(FleetVehicle).where(FleetVehicle.id == vehicle_id, FleetVehicle.tenant_id == tenant_id))
    await db.commit()


# --- Trailers -----------------------------------------------------------------

class TrailerOut(BaseModel):
    id: str
    internal_code: str | None = None
    registration_plate: str | None = None
    trailer_type: str | None = None
    status: str = "active"
    operating_company_id: str | None = None
    notes: str | None = None


class TrailersListOut(BaseModel):
    items: list[TrailerOut]


class TrailerCreateIn(BaseModel):
    internal_code: str | None = Field(None, max_length=64)
    registration_plate: str | None = Field(None, max_length=32)
    trailer_type: str | None = Field(None, max_length=64)
    status: str = Field(default="active", max_length=32)
    operating_company_id: str | None = None
    notes: str | None = None


class TrailerPatchIn(BaseModel):
    internal_code: str | None = Field(None, max_length=64)
    registration_plate: str | None = Field(None, max_length=32)
    trailer_type: str | None = Field(None, max_length=64)
    status: str | None = Field(None, max_length=32)
    operating_company_id: str | None = None
    notes: str | None = None


def _trailer_out(r: FleetTrailer) -> TrailerOut:
    return TrailerOut(
        id=r.id,
        internal_code=r.internal_code,
        registration_plate=r.registration_plate,
        trailer_type=r.trailer_type,
        status=r.status,
        operating_company_id=r.operating_company_id,
        notes=r.notes,
    )


async def _trailer_for_tenant(db: AsyncSession, tenant_id: str, tid: str) -> FleetTrailer | None:
    res = await db.execute(
        select(FleetTrailer).where(FleetTrailer.id == tid, FleetTrailer.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


@router.get("/trailers", response_model=TrailersListOut)
async def list_trailers(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TrailersListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    res = await db.execute(
        select(FleetTrailer)
        .where(FleetTrailer.tenant_id == tenant_id)
        .order_by(FleetTrailer.internal_code.asc(), FleetTrailer.registration_plate.asc(), FleetTrailer.id.asc())
    )
    return TrailersListOut(items=[_trailer_out(r) for r in res.scalars().all()])


@router.post("/trailers", response_model=TrailerOut, status_code=status.HTTP_201_CREATED)
async def create_trailer(
    body: TrailerCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TrailerOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if body.operating_company_id and not await _company_in_tenant(db, tenant_id, body.operating_company_id):
        raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    row = FleetTrailer(
        id=str(uuid4()),
        tenant_id=tenant_id,
        internal_code=body.internal_code.strip() if body.internal_code else None,
        registration_plate=body.registration_plate.strip() if body.registration_plate else None,
        trailer_type=body.trailer_type.strip() if body.trailer_type else None,
        status=(body.status or "active").strip() or "active",
        operating_company_id=body.operating_company_id,
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _trailer_out(row)


@router.get("/trailers/{trailer_id}", response_model=TrailerOut)
async def get_trailer(
    trailer_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TrailerOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _trailer_for_tenant(db, tenant_id, trailer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trailer not found")
    return _trailer_out(row)


@router.patch("/trailers/{trailer_id}", response_model=TrailerOut)
async def patch_trailer(
    trailer_id: str,
    body: TrailerPatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TrailerOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _trailer_for_tenant(db, tenant_id, trailer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trailer not found")
    data = body.model_dump(exclude_unset=True)
    if "operating_company_id" in data and data["operating_company_id"]:
        if not await _company_in_tenant(db, tenant_id, str(data["operating_company_id"])):
            raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    for key, value in data.items():
        if key in ("internal_code", "registration_plate", "trailer_type", "notes") and value is not None:
            setattr(row, key, str(value).strip() if isinstance(value, str) else value)
        elif key == "status" and value is not None:
            setattr(row, key, str(value).strip() or "active")
        elif key == "operating_company_id":
            setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return _trailer_out(row)


@router.delete("/trailers/{trailer_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_trailer(
    trailer_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _trailer_for_tenant(db, tenant_id, trailer_id) is None:
        raise HTTPException(status_code=404, detail="trailer not found")
    await db.execute(sql_delete(FleetTrailer).where(FleetTrailer.id == trailer_id, FleetTrailer.tenant_id == tenant_id))
    await db.commit()


# --- Drivers ------------------------------------------------------------------

class DriverOut(BaseModel):
    id: str
    display_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    status: str = "active"
    operating_company_id: str | None = None
    workforce_employee_id: str | None = None
    phone: str | None = None
    notes: str | None = None


class DriversListOut(BaseModel):
    items: list[DriverOut]


class DriverCreateIn(BaseModel):
    display_code: str | None = Field(None, max_length=64)
    first_name: str | None = Field(None, max_length=128)
    last_name: str | None = Field(None, max_length=128)
    status: str = Field(default="active", max_length=32)
    operating_company_id: str | None = None
    workforce_employee_id: str | None = None
    phone: str | None = Field(None, max_length=64)
    notes: str | None = None


class DriverPatchIn(BaseModel):
    display_code: str | None = Field(None, max_length=64)
    first_name: str | None = Field(None, max_length=128)
    last_name: str | None = Field(None, max_length=128)
    status: str | None = Field(None, max_length=32)
    operating_company_id: str | None = None
    workforce_employee_id: str | None = None
    phone: str | None = Field(None, max_length=64)
    notes: str | None = None


def _driver_out(r: FleetDriver) -> DriverOut:
    return DriverOut(
        id=r.id,
        display_code=r.display_code,
        first_name=r.first_name,
        last_name=r.last_name,
        status=r.status,
        operating_company_id=r.operating_company_id,
        workforce_employee_id=r.workforce_employee_id,
        phone=r.phone,
        notes=r.notes,
    )


async def _driver_for_tenant(db: AsyncSession, tenant_id: str, did: str) -> FleetDriver | None:
    res = await db.execute(
        select(FleetDriver).where(FleetDriver.id == did, FleetDriver.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


@router.get("/drivers", response_model=DriversListOut)
async def list_drivers(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> DriversListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    res = await db.execute(
        select(FleetDriver)
        .where(FleetDriver.tenant_id == tenant_id)
        .order_by(FleetDriver.display_code.asc(), FleetDriver.last_name.asc(), FleetDriver.id.asc())
    )
    return DriversListOut(items=[_driver_out(r) for r in res.scalars().all()])


@router.post("/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
async def create_driver(
    body: DriverCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> DriverOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if body.operating_company_id and not await _company_in_tenant(db, tenant_id, body.operating_company_id):
        raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    if body.workforce_employee_id and not await _workforce_in_tenant(db, tenant_id, body.workforce_employee_id):
        raise HTTPException(status_code=400, detail="workforce_employee_id not found in tenant")
    row = FleetDriver(
        id=str(uuid4()),
        tenant_id=tenant_id,
        display_code=body.display_code.strip() if body.display_code else None,
        first_name=body.first_name.strip() if body.first_name else None,
        last_name=body.last_name.strip() if body.last_name else None,
        status=(body.status or "active").strip() or "active",
        operating_company_id=body.operating_company_id,
        workforce_employee_id=body.workforce_employee_id,
        phone=body.phone.strip() if body.phone else None,
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _driver_out(row)


@router.get("/drivers/{driver_id}", response_model=DriverOut)
async def get_driver(
    driver_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> DriverOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _driver_for_tenant(db, tenant_id, driver_id)
    if row is None:
        raise HTTPException(status_code=404, detail="driver not found")
    return _driver_out(row)


@router.patch("/drivers/{driver_id}", response_model=DriverOut)
async def patch_driver(
    driver_id: str,
    body: DriverPatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> DriverOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _driver_for_tenant(db, tenant_id, driver_id)
    if row is None:
        raise HTTPException(status_code=404, detail="driver not found")
    data = body.model_dump(exclude_unset=True)
    if "operating_company_id" in data and data["operating_company_id"]:
        if not await _company_in_tenant(db, tenant_id, str(data["operating_company_id"])):
            raise HTTPException(status_code=400, detail="operating_company_id not found in tenant")
    if "workforce_employee_id" in data and data["workforce_employee_id"]:
        if not await _workforce_in_tenant(db, tenant_id, str(data["workforce_employee_id"])):
            raise HTTPException(status_code=400, detail="workforce_employee_id not found in tenant")
    for key, value in data.items():
        if key in ("display_code", "first_name", "last_name", "phone", "notes") and value is not None:
            setattr(row, key, str(value).strip() if isinstance(value, str) else value)
        elif key == "status" and value is not None:
            setattr(row, key, str(value).strip() or "active")
        elif key in ("operating_company_id", "workforce_employee_id"):
            setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return _driver_out(row)


@router.delete("/drivers/{driver_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_driver(
    driver_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _driver_for_tenant(db, tenant_id, driver_id) is None:
        raise HTTPException(status_code=404, detail="driver not found")
    await db.execute(sql_delete(FleetDriver).where(FleetDriver.id == driver_id, FleetDriver.tenant_id == tenant_id))
    await db.commit()
