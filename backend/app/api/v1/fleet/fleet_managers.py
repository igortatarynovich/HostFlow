"""Fleet park: assign CRM users as managers of vehicles and drivers."""

from __future__ import annotations

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
from backend.app.models.fleet_driver_manager import FleetDriverManager
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.fleet_vehicle_manager import FleetVehicleManager
from backend.app.services import fleet_resource_managers as frm

router = APIRouter(tags=["fleet-managers"])


class ManagerItemOut(BaseModel):
    id: str
    user_id: str
    label: str


class ManagersListOut(BaseModel):
    items: list[ManagerItemOut]


class ManagerAttachIn(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=36)


async def _vehicle_for_tenant(db: AsyncSession, tenant_id: str, vid: str) -> FleetVehicle | None:
    res = await db.execute(
        select(FleetVehicle).where(FleetVehicle.id == vid, FleetVehicle.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def _driver_for_tenant(db: AsyncSession, tenant_id: str, did: str) -> FleetDriver | None:
    res = await db.execute(
        select(FleetDriver).where(FleetDriver.id == did, FleetDriver.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def _v_mgr_row(db: AsyncSession, tenant_id: str, vehicle_id: str, row_id: str) -> FleetVehicleManager | None:
    res = await db.execute(
        select(FleetVehicleManager).where(
            FleetVehicleManager.id == row_id,
            FleetVehicleManager.vehicle_id == vehicle_id,
            FleetVehicleManager.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


async def _d_mgr_row(db: AsyncSession, tenant_id: str, driver_id: str, row_id: str) -> FleetDriverManager | None:
    res = await db.execute(
        select(FleetDriverManager).where(
            FleetDriverManager.id == row_id,
            FleetDriverManager.fleet_driver_id == driver_id,
            FleetDriverManager.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


# --- Vehicle managers ---------------------------------------------------------


@router.get("/vehicles/{vehicle_id}/managers", response_model=ManagersListOut)
async def list_vehicle_managers(
    vehicle_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> ManagersListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _vehicle_for_tenant(db, tenant_id, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    m = await frm.batch_vehicle_managers(db, tenant_id, [vehicle_id])
    tuples = m.get(vehicle_id, [])
    items = [ManagerItemOut(id=a, user_id=b, label=c) for a, b, c in tuples]
    return ManagersListOut(items=items)


@router.post("/vehicles/{vehicle_id}/managers", response_model=ManagerItemOut, status_code=status.HTTP_201_CREATED)
async def add_vehicle_manager(
    vehicle_id: str,
    body: ManagerAttachIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> ManagerItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _vehicle_for_tenant(db, tenant_id, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    if not await frm.user_can_be_fleet_manager(db, tenant_id, body.user_id):
        raise HTTPException(status_code=400, detail="user_id is not an active member of this tenant")
    row = FleetVehicleManager(id=str(uuid4()), tenant_id=tenant_id, vehicle_id=vehicle_id, user_id=body.user_id)
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="this user is already a manager for this vehicle") from exc
    batch = await frm.batch_vehicle_managers(db, tenant_id, [vehicle_id])
    for mid, uid, lbl in batch.get(vehicle_id, []):
        if mid == row.id:
            return ManagerItemOut(id=mid, user_id=uid, label=lbl)
    return ManagerItemOut(id=row.id, user_id=row.user_id, label=row.user_id[:8])


@router.delete("/vehicles/{vehicle_id}/managers/{membership_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_vehicle_manager(
    vehicle_id: str,
    membership_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _v_mgr_row(db, tenant_id, vehicle_id, membership_id) is None:
        raise HTTPException(status_code=404, detail="manager assignment not found")
    await db.execute(
        sql_delete(FleetVehicleManager).where(
            FleetVehicleManager.id == membership_id,
            FleetVehicleManager.vehicle_id == vehicle_id,
            FleetVehicleManager.tenant_id == tenant_id,
        )
    )
    await db.commit()


# --- Driver managers ----------------------------------------------------------


@router.get("/drivers/{driver_id}/managers", response_model=ManagersListOut)
async def list_driver_managers(
    driver_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> ManagersListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _driver_for_tenant(db, tenant_id, driver_id) is None:
        raise HTTPException(status_code=404, detail="driver not found")
    m = await frm.batch_driver_managers(db, tenant_id, [driver_id])
    tuples = m.get(driver_id, [])
    items = [ManagerItemOut(id=a, user_id=b, label=c) for a, b, c in tuples]
    return ManagersListOut(items=items)


@router.post("/drivers/{driver_id}/managers", response_model=ManagerItemOut, status_code=status.HTTP_201_CREATED)
async def add_driver_manager(
    driver_id: str,
    body: ManagerAttachIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> ManagerItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _driver_for_tenant(db, tenant_id, driver_id) is None:
        raise HTTPException(status_code=404, detail="driver not found")
    if not await frm.user_can_be_fleet_manager(db, tenant_id, body.user_id):
        raise HTTPException(status_code=400, detail="user_id is not an active member of this tenant")
    row = FleetDriverManager(id=str(uuid4()), tenant_id=tenant_id, fleet_driver_id=driver_id, user_id=body.user_id)
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="this user is already a manager for this driver") from exc
    batch = await frm.batch_driver_managers(db, tenant_id, [driver_id])
    for mid, uid, lbl in batch.get(driver_id, []):
        if mid == row.id:
            return ManagerItemOut(id=mid, user_id=uid, label=lbl)
    return ManagerItemOut(id=row.id, user_id=row.user_id, label=row.user_id[:8])


@router.delete("/drivers/{driver_id}/managers/{membership_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_driver_manager(
    driver_id: str,
    membership_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _d_mgr_row(db, tenant_id, driver_id, membership_id) is None:
        raise HTTPException(status_code=404, detail="manager assignment not found")
    await db.execute(
        sql_delete(FleetDriverManager).where(
            FleetDriverManager.id == membership_id,
            FleetDriverManager.fleet_driver_id == driver_id,
            FleetDriverManager.tenant_id == tenant_id,
        )
    )
    await db.commit()
