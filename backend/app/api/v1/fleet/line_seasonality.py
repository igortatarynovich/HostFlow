"""Operating-line seasonality from operational data (assignments + line roster), not manual factors."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Literal, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.fleet_assignment import FleetAssignment
from backend.app.models.fleet_operating_line import FleetOperatingLine
from backend.app.models.fleet_operating_line_driver import FleetOperatingLineDriver
from backend.app.models.fleet_operating_line_vehicle import FleetOperatingLineVehicle

router = APIRouter(tags=["fleet-line-seasonality"])

_EPS = 1e-6


def _dt_to_date(d: datetime) -> date:
    if d.tzinfo:
        return d.astimezone(timezone.utc).date()
    return d.date()


def _first_day_n_months_ago(steps: int) -> date:
    y, m = date.today().year, date.today().month
    for _ in range(steps):
        if m == 1:
            y -= 1
            m = 12
        else:
            m -= 1
    return date(y, m, 1)


def _month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _iter_months(window_start: date, window_end: date):
    cur = window_start.replace(day=1)
    while cur <= window_end:
        yield cur, _month_end(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def _overlap_days(a_start: date, a_end: date, b_start: date, b_end: date) -> int:
    lo = max(a_start, b_start)
    hi = min(a_end, b_end)
    if hi < lo:
        return 0
    return (hi - lo).days + 1


async def _line_for_tenant(db: AsyncSession, tenant_id: str, line_id: str) -> FleetOperatingLine | None:
    res = await db.execute(
        select(FleetOperatingLine).where(
            FleetOperatingLine.id == line_id,
            FleetOperatingLine.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


def _normalize_raw(raw: list[float]) -> tuple[list[float], bool, str | None]:
    total = sum(raw)
    if total < _EPS:
        return [1.0] * 12, True, "no overlap in period"
    mean_w = total / 12.0
    return [round((v / mean_w) if mean_w > 0 else 1.0, 4) for v in raw], False, None


def _accumulate_overlap_months(
    window_start: date,
    window_end: date,
    intervals: list[tuple[date, date]],
) -> list[float]:
    raw = [0.0] * 12
    for month_start, month_end in _iter_months(window_start, window_end):
        idx = month_start.month - 1
        for a_start, a_end in intervals:
            raw[idx] += float(_overlap_days(a_start, a_end, month_start, month_end))
    return raw


class MonthSeries(BaseModel):
    raw_by_month_index: list[float] = Field(..., min_length=12, max_length=12)
    months_1_to_12: list[float] = Field(..., min_length=12, max_length=12)
    insufficient_data: bool = False
    detail: str | None = None


class SeasonalityFromDataOut(BaseModel):
    line_id: str
    period_from: date
    period_to: date
    months_1_to_12: list[float] = Field(..., min_length=12, max_length=12)
    source: Literal["assignments", "roster", "blend"]
    insufficient_data: bool = False
    detail: str | None = None
    blend_weights: dict[str, float] | None = None
    assignments: MonthSeries | None = None
    roster: MonthSeries | None = None
    raw_assignment_days_by_month: list[float] | None = Field(
        None,
        description="Same as assignments.raw_by_month_index when assignments were computed (backward compatibility).",
    )


def _parse_sources(s: str) -> set[str]:
    parts = {p.strip().lower() for p in (s or "").split(",") if p.strip()}
    allowed = {"assignments", "roster"}
    bad = parts - allowed
    if bad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown sources: {sorted(bad)}; allowed: assignments, roster",
        )
    if not parts:
        parts.add("assignments")
    return parts


async def _raw_assignments(
    db: AsyncSession,
    tenant_id: str,
    line_id: str,
    window_start: date,
    window_end: date,
) -> list[float]:
    res = await db.execute(
        select(FleetAssignment).where(
            FleetAssignment.tenant_id == tenant_id,
            FleetAssignment.line_id == line_id,
            FleetAssignment.service_start <= window_end,
            or_(FleetAssignment.service_end.is_(None), FleetAssignment.service_end >= window_start),
        )
    )
    rows = list(res.scalars().all())
    intervals: list[tuple[date, date]] = []
    for row in rows:
        a_start = row.service_start
        cap = row.service_end if row.service_end is not None else window_end
        a_end = cap if cap >= a_start else a_start
        intervals.append((a_start, a_end))
    return _accumulate_overlap_months(window_start, window_end, intervals)


async def _raw_roster(
    db: AsyncSession,
    tenant_id: str,
    line_id: str,
    window_start: date,
    window_end: date,
) -> list[float]:
    intervals: list[tuple[date, date]] = []

    dr_res = await db.execute(
        select(FleetOperatingLineDriver).where(
            FleetOperatingLineDriver.tenant_id == tenant_id,
            FleetOperatingLineDriver.line_id == line_id,
        )
    )
    for row in dr_res.scalars().all():
        a_start = row.effective_from or window_start
        a_end = row.effective_to if row.effective_to is not None else window_end
        if a_end < window_start or a_start > window_end:
            continue
        intervals.append((max(a_start, window_start), min(a_end, window_end)))

    ve_res = await db.execute(
        select(FleetOperatingLineVehicle).where(
            FleetOperatingLineVehicle.tenant_id == tenant_id,
            FleetOperatingLineVehicle.line_id == line_id,
        )
    )
    for row in ve_res.scalars().all():
        start_d = _dt_to_date(row.created_at)
        if start_d > window_end:
            continue
        a_start = max(start_d, window_start)
        a_end = window_end
        intervals.append((a_start, a_end))

    return _accumulate_overlap_months(window_start, window_end, intervals)


def _blend_two_raw(
    raw_a: list[float],
    raw_b: list[float],
    wa: float,
    wb: float,
) -> tuple[list[float], bool, str | None]:
    has_a = sum(raw_a) >= _EPS
    has_b = sum(raw_b) >= _EPS
    if not has_a and not has_b:
        return [1.0] * 12, True, "no data in selected sources"
    if not has_a:
        fac, ins, det = _normalize_raw(raw_b)
        return fac, ins, det
    if not has_b:
        fac, ins, det = _normalize_raw(raw_a)
        return fac, ins, det
    comb = [wa * raw_a[i] + wb * raw_b[i] for i in range(12)]
    return _normalize_raw(comb)


@router.get("/operating-lines/{line_id}/seasonality-from-data", response_model=SeasonalityFromDataOut)
async def get_line_seasonality_from_data(
    line_id: str,
    months_back: int = Query(
        24,
        ge=12,
        le=60,
        description="How many whole calendar months to look back from today (inclusive).",
    ),
    sources: str = Query(
        "assignments",
        description="Comma-separated: `assignments`, `roster` (line driver + vehicle membership exposure).",
    ),
    weight_assignments: float = Query(
        1.0,
        ge=0.0,
        le=1.0,
        description="Blend weight for assignments when multiple sources are requested.",
    ),
    weight_roster: float = Query(
        0.0,
        ge=0.0,
        le=1.0,
        description="Blend weight for roster-based curve when multiple sources are requested.",
    ),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> SeasonalityFromDataOut:
    """Seasonality from **data**: fleet assignments and/or **roster** on the line.

    Roster uses driver memberships (`effective_from` / `effective_to`) and vehicle memberships
    (`created_at` … end of window). Weights are normalized to sum to 1 among selected sources.
    Manual `seasonality_month_factors` on the line is not used here.
    """
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)

    line = await _line_for_tenant(db, tenant_id, line_id)
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="operating line not found")

    req = _parse_sources(sources)
    window_end = date.today()
    window_start = _first_day_n_months_ago(months_back - 1)

    wa = weight_assignments if "assignments" in req else 0.0
    wr = weight_roster if "roster" in req else 0.0

    if len(req) == 1:
        if "assignments" in req:
            wa, wr = 1.0, 0.0
        else:
            wa, wr = 0.0, 1.0
    else:
        s = wa + wr
        if s <= _EPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="weight_assignments + weight_roster must be > 0 when using multiple sources",
            )
        wa, wr = wa / s, wr / s

    raw_asn: list[float] | None = None
    raw_rs: list[float] | None = None

    if "assignments" in req:
        raw_asn = await _raw_assignments(db, tenant_id, line_id, window_start, window_end)
    if "roster" in req:
        raw_rs = await _raw_roster(db, tenant_id, line_id, window_start, window_end)

    asn_series: MonthSeries | None = None
    roster_series: MonthSeries | None = None

    if raw_asn is not None:
        fac, ins, det = _normalize_raw(raw_asn)
        asn_series = MonthSeries(
            raw_by_month_index=raw_asn,
            months_1_to_12=fac,
            insufficient_data=ins,
            detail=det,
        )

    if raw_rs is not None:
        fac_r, ins_r, det_r = _normalize_raw(raw_rs)
        roster_series = MonthSeries(
            raw_by_month_index=raw_rs,
            months_1_to_12=fac_r,
            insufficient_data=ins_r,
            detail=det_r,
        )

    if len(req) == 1:
        if "assignments" in req:
            assert asn_series is not None and raw_asn is not None
            return SeasonalityFromDataOut(
                line_id=line_id,
                period_from=window_start,
                period_to=window_end,
                months_1_to_12=asn_series.months_1_to_12,
                source="assignments",
                insufficient_data=asn_series.insufficient_data,
                detail=asn_series.detail,
                assignments=asn_series,
                raw_assignment_days_by_month=list(raw_asn),
            )
        assert roster_series is not None and raw_rs is not None
        return SeasonalityFromDataOut(
            line_id=line_id,
            period_from=window_start,
            period_to=window_end,
            months_1_to_12=roster_series.months_1_to_12,
            source="roster",
            insufficient_data=roster_series.insufficient_data,
            detail=roster_series.detail,
            roster=roster_series,
            blend_weights={"roster": 1.0},
        )

    assert raw_asn is not None and raw_rs is not None and asn_series is not None and roster_series is not None
    blended, ins_bl, det_bl = _blend_two_raw(raw_asn, raw_rs, wa, wr)
    top_detail = det_bl if ins_bl else None

    return SeasonalityFromDataOut(
        line_id=line_id,
        period_from=window_start,
        period_to=window_end,
        months_1_to_12=blended,
        source="blend",
        insufficient_data=ins_bl,
        detail=top_detail,
        blend_weights={"assignments": round(wa, 4), "roster": round(wr, 4)},
        assignments=asn_series,
        roster=roster_series,
        raw_assignment_days_by_month=list(raw_asn),
    )
