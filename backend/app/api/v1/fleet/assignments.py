"""Fleet operational assignments (vehicle + optional trailer/driver on a line)."""

from __future__ import annotations

from datetime import date
from typing import Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete as sql_delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.fleet_assignment import FleetAssignment
from backend.app.models.fleet_driver import FleetDriver
from backend.app.models.fleet_operating_line import FleetOperatingLine
from backend.app.models.fleet_trailer import FleetTrailer
from backend.app.models.fleet_vehicle import FleetVehicle

router = APIRouter(tags=["fleet-assignments"])

_ALLOWED_STATUS = frozenset({"planned", "active", "completed", "cancelled"})


def _vehicle_label(v: FleetVehicle) -> str:
    return v.internal_code or v.registration_plate or " ".join(filter(None, [v.brand, v.model])) or v.id[:8]


def _trailer_label(t: FleetTrailer) -> str:
    return t.internal_code or t.registration_plate or t.trailer_type or t.id[:8]


def _driver_label(d: FleetDriver) -> str:
    return d.display_code or " ".join(filter(None, [d.first_name, d.last_name])) or d.id[:8]


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


async def _trailer_for_tenant(db: AsyncSession, tenant_id: str, trailer_id: str) -> FleetTrailer | None:
    res = await db.execute(
        select(FleetTrailer).where(FleetTrailer.id == trailer_id, FleetTrailer.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def _driver_for_tenant(db: AsyncSession, tenant_id: str, driver_id: str) -> FleetDriver | None:
    res = await db.execute(
        select(FleetDriver).where(FleetDriver.id == driver_id, FleetDriver.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def _assignment_for_tenant(
    db: AsyncSession, tenant_id: str, assignment_id: str
) -> FleetAssignment | None:
    res = await db.execute(
        select(FleetAssignment).where(
            FleetAssignment.id == assignment_id,
            FleetAssignment.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


def _validate_dates(service_start: date, service_end: date | None) -> None:
    if service_end is not None and service_end < service_start:
        raise HTTPException(status_code=400, detail="service_end must be on or after service_start")


def _validate_status(status_val: str) -> None:
    if status_val not in _ALLOWED_STATUS:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(_ALLOWED_STATUS))}",
        )


class AssignmentOut(BaseModel):
    id: str
    line_id: str
    line_name: str
    vehicle_id: str
    vehicle_label: str
    trailer_id: str | None = None
    trailer_label: str | None = None
    primary_driver_id: str | None = None
    primary_driver_label: str | None = None
    status: str
    service_start: date
    service_end: date | None = None
    notes: str | None = None


class AssignmentsListOut(BaseModel):
    items: list[AssignmentOut]


class AssignmentCreateIn(BaseModel):
    line_id: str = Field(..., min_length=1, max_length=36)
    vehicle_id: str = Field(..., min_length=1, max_length=36)
    trailer_id: str | None = Field(None, max_length=36)
    primary_driver_id: str | None = Field(None, max_length=36)
    status: str = Field(default="planned", max_length=32)
    service_start: date
    service_end: date | None = None
    notes: str | None = None


class AssignmentPatchIn(BaseModel):
    trailer_id: str | None = Field(None, max_length=36)
    primary_driver_id: str | None = Field(None, max_length=36)
    status: str | None = Field(None, max_length=32)
    service_start: date | None = None
    service_end: date | None = None
    notes: str | None = None


async def _to_out(db: AsyncSession, tenant_id: str, row: FleetAssignment) -> AssignmentOut:
    line = await _line_for_tenant(db, tenant_id, row.line_id)
    line_name = line.name if line else row.line_id[:8]
    v = await _vehicle_for_tenant(db, tenant_id, row.vehicle_id)
    vehicle_label = _vehicle_label(v) if v else row.vehicle_id[:8]
    trailer_label: str | None = None
    if row.trailer_id:
        tr = await _trailer_for_tenant(db, tenant_id, row.trailer_id)
        trailer_label = _trailer_label(tr) if tr else row.trailer_id[:8]
    primary_driver_label: str | None = None
    if row.primary_driver_id:
        d = await _driver_for_tenant(db, tenant_id, row.primary_driver_id)
        primary_driver_label = _driver_label(d) if d else row.primary_driver_id[:8]
    return AssignmentOut(
        id=row.id,
        line_id=row.line_id,
        line_name=line_name,
        vehicle_id=row.vehicle_id,
        vehicle_label=vehicle_label,
        trailer_id=row.trailer_id,
        trailer_label=trailer_label,
        primary_driver_id=row.primary_driver_id,
        primary_driver_label=primary_driver_label,
        status=row.status,
        service_start=row.service_start,
        service_end=row.service_end,
        notes=row.notes,
    )


@router.get("/assignments", response_model=AssignmentsListOut)
async def list_assignments(
    line_id: str | None = Query(None, max_length=36),
    status_filter: str | None = Query(None, alias="status", max_length=32),
    service_from: date | None = Query(
        None,
        description="Include assignments that overlap this date or later (inclusive), using service period.",
    ),
    service_to: date | None = Query(
        None,
        description="Include assignments that overlap this date or earlier (inclusive), using service period.",
    ),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> AssignmentsListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    stmt = select(FleetAssignment).where(FleetAssignment.tenant_id == tenant_id)
    if line_id:
        stmt = stmt.where(FleetAssignment.line_id == line_id)
    if status_filter:
        stmt = stmt.where(FleetAssignment.status == status_filter)
    if service_from is not None and service_to is not None:
        stmt = stmt.where(
            and_(
                FleetAssignment.service_start <= service_to,
                or_(
                    FleetAssignment.service_end.is_(None),
                    FleetAssignment.service_end >= service_from,
                ),
            )
        )
    elif service_from is not None:
        stmt = stmt.where(
            or_(
                FleetAssignment.service_end.is_(None),
                FleetAssignment.service_end >= service_from,
            )
        )
    elif service_to is not None:
        stmt = stmt.where(FleetAssignment.service_start <= service_to)
    stmt = stmt.order_by(FleetAssignment.service_start.desc(), FleetAssignment.id.asc())
    res = await db.execute(stmt)
    rows = list(res.scalars().all())
    items = [await _to_out(db, tenant_id, r) for r in rows]
    return AssignmentsListOut(items=items)


@router.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: AssignmentCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> AssignmentOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _line_for_tenant(db, tenant_id, body.line_id) is None:
        raise HTTPException(status_code=400, detail="line_id not found in tenant")
    if await _vehicle_for_tenant(db, tenant_id, body.vehicle_id) is None:
        raise HTTPException(status_code=400, detail="vehicle_id not found in tenant")
    if body.trailer_id and await _trailer_for_tenant(db, tenant_id, body.trailer_id) is None:
        raise HTTPException(status_code=400, detail="trailer_id not found in tenant")
    if body.primary_driver_id and await _driver_for_tenant(db, tenant_id, body.primary_driver_id) is None:
        raise HTTPException(status_code=400, detail="primary_driver_id not found in tenant")
    _validate_status(body.status.strip())
    _validate_dates(body.service_start, body.service_end)
    row = FleetAssignment(
        id=str(uuid4()),
        tenant_id=tenant_id,
        line_id=body.line_id,
        vehicle_id=body.vehicle_id,
        trailer_id=body.trailer_id,
        primary_driver_id=body.primary_driver_id,
        status=body.status.strip(),
        service_start=body.service_start,
        service_end=body.service_end,
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return await _to_out(db, tenant_id, row)


@router.get("/assignments/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    assignment_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> AssignmentOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _assignment_for_tenant(db, tenant_id, assignment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="assignment not found")
    return await _to_out(db, tenant_id, row)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentOut)
async def patch_assignment(
    assignment_id: str,
    body: AssignmentPatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> AssignmentOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _assignment_for_tenant(db, tenant_id, assignment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="assignment not found")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        _validate_status(str(data["status"]).strip())
        row.status = str(data["status"]).strip()
    if "trailer_id" in data:
        tid = data["trailer_id"]
        if tid and await _trailer_for_tenant(db, tenant_id, str(tid)) is None:
            raise HTTPException(status_code=400, detail="trailer_id not found in tenant")
        row.trailer_id = tid
    if "primary_driver_id" in data:
        did = data["primary_driver_id"]
        if did and await _driver_for_tenant(db, tenant_id, str(did)) is None:
            raise HTTPException(status_code=400, detail="primary_driver_id not found in tenant")
        row.primary_driver_id = did
    if "service_start" in data and data["service_start"] is not None:
        row.service_start = data["service_start"]
    if "service_end" in data:
        row.service_end = data["service_end"]
    if "notes" in data:
        row.notes = (str(data["notes"]).strip() or None) if data["notes"] is not None else None
    _validate_dates(row.service_start, row.service_end)
    await db.commit()
    await db.refresh(row)
    return await _to_out(db, tenant_id, row)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_assignment(
    assignment_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _assignment_for_tenant(db, tenant_id, assignment_id) is None:
        raise HTTPException(status_code=404, detail="assignment not found")
    await db.execute(
        sql_delete(FleetAssignment).where(
            FleetAssignment.id == assignment_id,
            FleetAssignment.tenant_id == tenant_id,
        )
    )
    await db.commit()
