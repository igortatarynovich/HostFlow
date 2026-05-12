"""Aggregated fleet dashboard counts for one tenant."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.fleet_assignment import FleetAssignment
from backend.app.models.fleet_driver import FleetDriver
from backend.app.models.fleet_operating_line import FleetOperatingLine
from backend.app.models.fleet_operating_line_driver import FleetOperatingLineDriver
from backend.app.models.fleet_operating_line_vehicle import FleetOperatingLineVehicle
from backend.app.models.fleet_trailer import FleetTrailer
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.fleet_work_model import FleetWorkModel

router = APIRouter(tags=["fleet-overview"])


class FleetOverviewOut(BaseModel):
    vehicles_total: int = 0
    vehicles_by_status: dict[str, int] = Field(default_factory=dict)
    trailers_total: int = 0
    trailers_by_status: dict[str, int] = Field(default_factory=dict)
    drivers_total: int = 0
    drivers_by_status: dict[str, int] = Field(default_factory=dict)
    drivers_with_workforce_total: int = 0
    operating_lines_total: int = 0
    operating_lines_by_status: dict[str, int] = Field(default_factory=dict)
    work_models_total: int = 0
    line_roster_vehicles_total: int = 0
    line_roster_drivers_total: int = 0
    line_roster_drivers_effective_today_total: int = 0
    assignments_total: int = 0
    assignments_by_status: dict[str, int] = Field(default_factory=dict)
    assignments_overlapping_today_utc_total: int = 0
    assignments_overlapping_month_utc_total: int = 0


def _norm_status(key: str) -> str:
    s = (key or "").strip().lower()
    return s if s else "unknown"


@router.get("/overview", response_model=FleetOverviewOut)
async def fleet_overview(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> FleetOverviewOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)

    vehicles_total = int(
        await db.scalar(
            select(func.count()).select_from(FleetVehicle).where(FleetVehicle.tenant_id == tenant_id)
        )
        or 0
    )
    trailers_total = int(
        await db.scalar(
            select(func.count()).select_from(FleetTrailer).where(FleetTrailer.tenant_id == tenant_id)
        )
        or 0
    )
    drivers_total = int(
        await db.scalar(
            select(func.count()).select_from(FleetDriver).where(FleetDriver.tenant_id == tenant_id)
        )
        or 0
    )
    drivers_with_workforce_total = int(
        await db.scalar(
            select(func.count())
            .select_from(FleetDriver)
            .where(
                FleetDriver.tenant_id == tenant_id,
                FleetDriver.workforce_employee_id.isnot(None),
            )
        )
        or 0
    )
    operating_lines_total = int(
        await db.scalar(
            select(func.count())
            .select_from(FleetOperatingLine)
            .where(FleetOperatingLine.tenant_id == tenant_id)
        )
        or 0
    )
    work_models_total = int(
        await db.scalar(
            select(func.count()).select_from(FleetWorkModel).where(FleetWorkModel.tenant_id == tenant_id)
        )
        or 0
    )
    line_roster_vehicles_total = int(
        await db.scalar(
            select(func.count())
            .select_from(FleetOperatingLineVehicle)
            .where(FleetOperatingLineVehicle.tenant_id == tenant_id)
        )
        or 0
    )
    line_roster_drivers_total = int(
        await db.scalar(
            select(func.count())
            .select_from(FleetOperatingLineDriver)
            .where(FleetOperatingLineDriver.tenant_id == tenant_id)
        )
        or 0
    )
    today_utc_date = datetime.now(timezone.utc).date()
    line_roster_drivers_effective_today_total = int(
        await db.scalar(
            select(func.count())
            .select_from(FleetOperatingLineDriver)
            .where(
                FleetOperatingLineDriver.tenant_id == tenant_id,
                or_(
                    FleetOperatingLineDriver.effective_from.is_(None),
                    FleetOperatingLineDriver.effective_from <= today_utc_date,
                ),
                or_(
                    FleetOperatingLineDriver.effective_to.is_(None),
                    FleetOperatingLineDriver.effective_to >= today_utc_date,
                ),
            )
        )
        or 0
    )
    assignments_total = int(
        await db.scalar(
            select(func.count()).select_from(FleetAssignment).where(FleetAssignment.tenant_id == tenant_id)
        )
        or 0
    )

    last_day = calendar.monthrange(today_utc_date.year, today_utc_date.month)[1]
    month_start_utc = date(today_utc_date.year, today_utc_date.month, 1)
    month_end_utc = date(today_utc_date.year, today_utc_date.month, last_day)
    svc_end = func.coalesce(FleetAssignment.service_end, FleetAssignment.service_start)

    assignments_overlapping_today_utc_total = int(
        await db.scalar(
            select(func.count())
            .select_from(FleetAssignment)
            .where(
                FleetAssignment.tenant_id == tenant_id,
                FleetAssignment.service_start <= today_utc_date,
                svc_end >= today_utc_date,
            )
        )
        or 0
    )
    assignments_overlapping_month_utc_total = int(
        await db.scalar(
            select(func.count())
            .select_from(FleetAssignment)
            .where(
                FleetAssignment.tenant_id == tenant_id,
                FleetAssignment.service_start <= month_end_utc,
                svc_end >= month_start_utc,
            )
        )
        or 0
    )

    v_rows = await db.execute(
        select(FleetVehicle.status, func.count(FleetVehicle.id))
        .where(FleetVehicle.tenant_id == tenant_id)
        .group_by(FleetVehicle.status)
    )
    vehicles_by_status: dict[str, int] = {}
    for status_val, cnt in v_rows.all():
        k = _norm_status(str(status_val or ""))
        vehicles_by_status[k] = int(cnt)

    t_rows = await db.execute(
        select(FleetTrailer.status, func.count(FleetTrailer.id))
        .where(FleetTrailer.tenant_id == tenant_id)
        .group_by(FleetTrailer.status)
    )
    trailers_by_status: dict[str, int] = {}
    for status_val, cnt in t_rows.all():
        k = _norm_status(str(status_val or ""))
        trailers_by_status[k] = int(cnt)

    d_rows = await db.execute(
        select(FleetDriver.status, func.count(FleetDriver.id))
        .where(FleetDriver.tenant_id == tenant_id)
        .group_by(FleetDriver.status)
    )
    drivers_by_status: dict[str, int] = {}
    for status_val, cnt in d_rows.all():
        k = _norm_status(str(status_val or ""))
        drivers_by_status[k] = int(cnt)

    ol_rows = await db.execute(
        select(FleetOperatingLine.status, func.count(FleetOperatingLine.id))
        .where(FleetOperatingLine.tenant_id == tenant_id)
        .group_by(FleetOperatingLine.status)
    )
    operating_lines_by_status: dict[str, int] = {}
    for status_val, cnt in ol_rows.all():
        k = _norm_status(str(status_val or ""))
        operating_lines_by_status[k] = int(cnt)

    a_rows = await db.execute(
        select(FleetAssignment.status, func.count(FleetAssignment.id))
        .where(FleetAssignment.tenant_id == tenant_id)
        .group_by(FleetAssignment.status)
    )
    assignments_by_status: dict[str, int] = {}
    for status_val, cnt in a_rows.all():
        k = _norm_status(str(status_val or ""))
        assignments_by_status[k] = int(cnt)

    return FleetOverviewOut(
        vehicles_total=vehicles_total,
        vehicles_by_status=vehicles_by_status,
        trailers_total=trailers_total,
        trailers_by_status=trailers_by_status,
        drivers_total=drivers_total,
        drivers_by_status=drivers_by_status,
        drivers_with_workforce_total=drivers_with_workforce_total,
        operating_lines_total=operating_lines_total,
        operating_lines_by_status=operating_lines_by_status,
        work_models_total=work_models_total,
        line_roster_vehicles_total=line_roster_vehicles_total,
        line_roster_drivers_total=line_roster_drivers_total,
        line_roster_drivers_effective_today_total=line_roster_drivers_effective_today_total,
        assignments_total=assignments_total,
        assignments_by_status=assignments_by_status,
        assignments_overlapping_today_utc_total=assignments_overlapping_today_utc_total,
        assignments_overlapping_month_utc_total=assignments_overlapping_month_utc_total,
    )
