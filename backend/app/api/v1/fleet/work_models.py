"""Fleet work models (rotation templates)."""

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
from backend.app.models.fleet_work_model import FleetWorkModel

router = APIRouter(tags=["fleet-work-models"])


def _validate_cycle(work_days: int, rest_days: int, cycle_length: int) -> None:
    if work_days < 1 or rest_days < 0 or cycle_length < 1:
        raise HTTPException(status_code=400, detail="work_days, rest_days, cycle_length must be positive where applicable")
    if work_days + rest_days != cycle_length:
        raise HTTPException(
            status_code=400,
            detail="work_days + rest_days must equal cycle_length",
        )


class WorkModelOut(BaseModel):
    id: str
    name: str
    work_days: int
    rest_days: int
    cycle_length: int
    notes: str | None = None


class WorkModelsListOut(BaseModel):
    items: list[WorkModelOut]


class WorkModelCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    work_days: int = Field(..., ge=1)
    rest_days: int = Field(..., ge=0)
    cycle_length: int = Field(..., ge=1)
    notes: str | None = None


class WorkModelPatchIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    work_days: int | None = Field(None, ge=1)
    rest_days: int | None = Field(None, ge=0)
    cycle_length: int | None = Field(None, ge=1)
    notes: str | None = None


def _out(r: FleetWorkModel) -> WorkModelOut:
    return WorkModelOut(
        id=r.id,
        name=r.name,
        work_days=r.work_days,
        rest_days=r.rest_days,
        cycle_length=r.cycle_length,
        notes=r.notes,
    )


async def _wm_for_tenant(db: AsyncSession, tenant_id: str, wm_id: str) -> FleetWorkModel | None:
    res = await db.execute(
        select(FleetWorkModel).where(FleetWorkModel.id == wm_id, FleetWorkModel.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


@router.get("/work-models", response_model=WorkModelsListOut)
async def list_work_models(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkModelsListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    res = await db.execute(
        select(FleetWorkModel).where(FleetWorkModel.tenant_id == tenant_id).order_by(FleetWorkModel.name.asc())
    )
    return WorkModelsListOut(items=[_out(r) for r in res.scalars().all()])


@router.post("/work-models", response_model=WorkModelOut, status_code=status.HTTP_201_CREATED)
async def create_work_model(
    body: WorkModelCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkModelOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    _validate_cycle(body.work_days, body.rest_days, body.cycle_length)
    row = FleetWorkModel(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name=body.name.strip(),
        work_days=body.work_days,
        rest_days=body.rest_days,
        cycle_length=body.cycle_length,
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _out(row)


@router.get("/work-models/{wm_id}", response_model=WorkModelOut)
async def get_work_model(
    wm_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkModelOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _wm_for_tenant(db, tenant_id, wm_id)
    if row is None:
        raise HTTPException(status_code=404, detail="work model not found")
    return _out(row)


@router.patch("/work-models/{wm_id}", response_model=WorkModelOut)
async def patch_work_model(
    wm_id: str,
    body: WorkModelPatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> WorkModelOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    row = await _wm_for_tenant(db, tenant_id, wm_id)
    if row is None:
        raise HTTPException(status_code=404, detail="work model not found")
    data = body.model_dump(exclude_unset=True)
    wd = data.get("work_days", row.work_days)
    rd = data.get("rest_days", row.rest_days)
    cl = data.get("cycle_length", row.cycle_length)
    if "work_days" in data or "rest_days" in data or "cycle_length" in data:
        _validate_cycle(int(wd), int(rd), int(cl))
    for key, value in data.items():
        if key == "name" and value is not None:
            setattr(row, key, str(value).strip())
        elif key in ("work_days", "rest_days", "cycle_length") and value is not None:
            setattr(row, key, int(value))
        elif key == "notes":
            setattr(row, key, (str(value).strip() or None) if value is not None else None)
    await db.commit()
    await db.refresh(row)
    return _out(row)


@router.delete("/work-models/{wm_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_work_model(
    wm_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if await _wm_for_tenant(db, tenant_id, wm_id) is None:
        raise HTTPException(status_code=404, detail="work model not found")
    try:
        await db.execute(sql_delete(FleetWorkModel).where(FleetWorkModel.id == wm_id, FleetWorkModel.tenant_id == tenant_id))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="cannot delete work model: still referenced by operating line drivers or vehicles",
        ) from exc
