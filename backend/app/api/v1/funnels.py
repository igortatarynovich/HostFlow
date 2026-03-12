"""API for universal Funnel model (candidate, lead, deal pipelines)."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.user import Role

router = APIRouter(prefix="/funnels", tags=["funnels"])

SYSTEM_STAGE_NEW = "new"
SYSTEM_STAGE_IN_PROGRESS = "in_progress"
SYSTEM_STAGE_HIRED = "hired"
SYSTEM_STAGE_DECLINED_OR_REJECTED = "declined_rejected"
SYSTEM_STAGES = {
    SYSTEM_STAGE_NEW,
    SYSTEM_STAGE_IN_PROGRESS,
    SYSTEM_STAGE_HIRED,
    SYSTEM_STAGE_DECLINED_OR_REJECTED,
}


def _infer_system_stage_from_code(code: str) -> str:
    c = (code or "").strip().lower()
    if c in {"new"}:
        return SYSTEM_STAGE_NEW
    if c in {"employed", "hired", "probation_ok"}:
        return SYSTEM_STAGE_HIRED
    if c in {"declined", "rejected"}:
        return SYSTEM_STAGE_DECLINED_OR_REJECTED
    return SYSTEM_STAGE_IN_PROGRESS


def _resolve_system_stage(value: Optional[str], code: str) -> str:
    if value is None or not str(value).strip():
        return _infer_system_stage_from_code(code)
    normalized = str(value).strip().lower()
    if normalized not in SYSTEM_STAGES:
        raise HTTPException(
            status_code=422,
            detail="system_stage must be one of: new, in_progress, hired, declined_rejected",
        )
    return normalized


class FunnelStageIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=255)
    system_stage: Optional[str] = Field(
        default=None,
        description="System skeleton stage: new | in_progress | hired | declined_rejected",
    )
    order: int = Field(0, ge=0)
    is_terminal: bool = False


class FunnelStageOut(BaseModel):
    id: str
    funnel_id: str
    code: str
    label: str
    system_stage: str
    order: int
    is_terminal: bool

    @classmethod
    def from_model(cls, s: FunnelStage) -> "FunnelStageOut":
        return cls(
            id=s.id,
            funnel_id=s.funnel_id,
            code=s.code,
            label=s.label,
            system_stage=s.system_stage,
            order=s.order,
            is_terminal=s.is_terminal,
        )


class FunnelIn(BaseModel):
    type: str = Field(..., pattern="^(candidate|lead|deal)$")
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False


class FunnelOut(BaseModel):
    id: str
    tenant_id: str
    type: str
    name: str
    is_default: bool
    stages: List[FunnelStageOut] = []

    @classmethod
    def from_model(cls, f: Funnel, stages: Optional[List[FunnelStage]] = None) -> "FunnelOut":
        stage_list = stages if stages is not None else list(f.stages) if hasattr(f, "stages") else []
        return cls(
            id=f.id,
            tenant_id=f.tenant_id,
            type=f.type,
            name=f.name,
            is_default=f.is_default,
            stages=[FunnelStageOut.from_model(s) for s in stage_list],
        )


@router.get("", response_model=List[FunnelOut])
@router.get("/", response_model=List[FunnelOut], include_in_schema=False)
async def list_funnels(
    type_filter: Optional[str] = Query(None, alias="type"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _user=Depends(get_current_user),
) -> List[FunnelOut]:
    """List funnels for tenant. Returns default funnel + any custom ones."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    stmt = select(Funnel).where(Funnel.tenant_id.in_([tenant_str, "default"]))
    if type_filter:
        stmt = stmt.where(Funnel.type == type_filter)
    stmt = stmt.order_by(Funnel.is_default.desc(), Funnel.name)
    result = await db.execute(stmt)
    funnels = result.scalars().all()

    out: List[FunnelOut] = []
    for f in funnels:
        stages_stmt = select(FunnelStage).where(FunnelStage.funnel_id == f.id).order_by(FunnelStage.order)
        stages_result = await db.execute(stages_stmt)
        stages = list(stages_result.scalars().all())
        out.append(FunnelOut.from_model(f, stages))
    return out


@router.get("/{funnel_id}", response_model=FunnelOut)
async def get_funnel(
    funnel_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _user=Depends(get_current_user),
) -> FunnelOut:
    """Get funnel with stages."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    result = await db.execute(
        select(Funnel).where(
            Funnel.id == funnel_id,
            Funnel.tenant_id.in_([tenant_str, "default"]),
        )
    )
    funnel = result.scalar_one_or_none()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")

    stages_result = await db.execute(
        select(FunnelStage).where(FunnelStage.funnel_id == funnel.id).order_by(FunnelStage.order)
    )
    stages = list(stages_result.scalars().all())
    return FunnelOut.from_model(funnel, stages)


@router.post("", response_model=FunnelOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FunnelOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_funnel(
    payload: FunnelIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _user=Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelOut:
    """Create a new funnel."""
    import uuid

    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    if payload.is_default:
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_str,
                Funnel.type == payload.type,
            )
        )
        unset_stmt = (
            select(Funnel).where(Funnel.tenant_id == tenant_str, Funnel.type == payload.type)
        )
        existing = await db.execute(unset_stmt)
        for f in existing.scalars().all():
            f.is_default = False

    funnel = Funnel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_str,
        type=payload.type,
        name=payload.name,
        is_default=payload.is_default,
    )
    db.add(funnel)
    await db.commit()
    await db.refresh(funnel)
    return FunnelOut.from_model(funnel, [])


@router.patch("/{funnel_id}", response_model=FunnelOut)
async def update_funnel(
    funnel_id: str,
    payload: FunnelIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _user=Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelOut:
    """Update funnel."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    result = await db.execute(
        select(Funnel).where(
            Funnel.id == funnel_id,
            Funnel.tenant_id == tenant_str,
        )
    )
    funnel = result.scalar_one_or_none()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")

    if payload.is_default and not funnel.is_default:
        unset = await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_str,
                Funnel.type == payload.type,
            )
        )
        for f in unset.scalars().all():
            f.is_default = False

    funnel.type = payload.type
    funnel.name = payload.name
    funnel.is_default = payload.is_default
    await db.commit()
    await db.refresh(funnel)

    stages_result = await db.execute(
        select(FunnelStage).where(FunnelStage.funnel_id == funnel.id).order_by(FunnelStage.order)
    )
    return FunnelOut.from_model(funnel, list(stages_result.scalars().all()))


@router.post("/{funnel_id}/stages", response_model=FunnelStageOut, status_code=status.HTTP_201_CREATED)
async def add_funnel_stage(
    funnel_id: str,
    payload: FunnelStageIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _user=Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelStageOut:
    """Add stage to funnel."""
    import uuid

    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    result = await db.execute(
        select(Funnel).where(
            Funnel.id == funnel_id,
            Funnel.tenant_id == tenant_str,
        )
    )
    funnel = result.scalar_one_or_none()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")

    existing = await db.execute(
        select(FunnelStage).where(
            FunnelStage.funnel_id == funnel_id,
            FunnelStage.code == payload.code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Stage code '{payload.code}' already exists")

    resolved_system_stage = _resolve_system_stage(payload.system_stage, payload.code)
    stage = FunnelStage(
        id=str(uuid.uuid4()),
        funnel_id=funnel_id,
        code=payload.code,
        label=payload.label,
        system_stage=resolved_system_stage,
        order=payload.order,
        is_terminal=payload.is_terminal or resolved_system_stage in {SYSTEM_STAGE_HIRED, SYSTEM_STAGE_DECLINED_OR_REJECTED},
    )
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return FunnelStageOut.from_model(stage)


@router.patch("/{funnel_id}/stages/{stage_id}", response_model=FunnelStageOut)
async def update_funnel_stage(
    funnel_id: str,
    stage_id: str,
    payload: FunnelStageIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _user=Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelStageOut:
    """Update funnel stage."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    funnel_result = await db.execute(
        select(Funnel).where(
            Funnel.id == funnel_id,
            Funnel.tenant_id == tenant_str,
        )
    )
    if not funnel_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Funnel not found")

    stage_result = await db.execute(
        select(FunnelStage).where(
            FunnelStage.id == stage_id,
            FunnelStage.funnel_id == funnel_id,
        )
    )
    stage = stage_result.scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    if payload.code != stage.code:
        dup = await db.execute(
            select(FunnelStage).where(
                FunnelStage.funnel_id == funnel_id,
                FunnelStage.code == payload.code,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Stage code '{payload.code}' already exists")

    resolved_system_stage = _resolve_system_stage(payload.system_stage, payload.code)
    stage.code = payload.code
    stage.label = payload.label
    stage.system_stage = resolved_system_stage
    stage.order = payload.order
    stage.is_terminal = payload.is_terminal or resolved_system_stage in {SYSTEM_STAGE_HIRED, SYSTEM_STAGE_DECLINED_OR_REJECTED}
    await db.commit()
    await db.refresh(stage)
    return FunnelStageOut.from_model(stage)


@router.delete("/{funnel_id}/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_funnel_stage(
    funnel_id: str,
    stage_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _user=Depends(require_roles(Role.admin)),
) -> None:
    """Delete funnel stage."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    funnel_result = await db.execute(
        select(Funnel).where(
            Funnel.id == funnel_id,
            Funnel.tenant_id == tenant_str,
        )
    )
    if not funnel_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Funnel not found")

    stage_result = await db.execute(
        select(FunnelStage).where(
            FunnelStage.id == stage_id,
            FunnelStage.funnel_id == funnel_id,
        )
    )
    stage = stage_result.scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    existing_stages = (
        await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == funnel_id))
    ).scalars().all()
    same_bucket_count = len(
        [s for s in existing_stages if str(getattr(s, "system_stage", "")).lower() == str(stage.system_stage).lower()]
    )
    if same_bucket_count <= 1:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot delete stage: each funnel must keep at least one stage mapped to each used system_stage bucket"
            ),
        )

    await db.delete(stage)
    await db.commit()
