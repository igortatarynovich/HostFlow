"""API endpoints for managing candidate stages (pipelines)."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate_stage import CandidateStageDict
from backend.app.models.user import Role

router = APIRouter(prefix="/candidate-stages", tags=["candidate-stages"])


class CandidateStageIn(BaseModel):
    """Payload for creating/updating candidate stage."""

    code: str = Field(..., min_length=1, max_length=50, description="Уникальный код этапа")
    label: str = Field(..., min_length=1, max_length=100, description="Название этапа")
    order: int = Field(0, ge=0, description="Порядок сортировки")
    active: bool = Field(True, description="Активен ли этап")


class CandidateStageOut(BaseModel):
    """Response model for candidate stage."""

    id: int
    tenant_id: Optional[str]
    code: str
    label: str
    order: int
    active: bool

    @classmethod
    def from_model(cls, stage: CandidateStageDict) -> "CandidateStageOut":
        """Create from ORM model."""
        return cls(
            id=stage.id,
            tenant_id=stage.tenant_id,
            code=stage.code,
            label=stage.label,
            order=stage.order,
            active=stage.active,
        )


@router.get("", response_model=List[CandidateStageOut])
@router.get("/", response_model=List[CandidateStageOut], include_in_schema=False)
async def list_candidate_stages(
    active: Optional[bool] = Query(None, description="Фильтр по активности"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
):
    """List all candidate stages for the tenant."""
    try:
        db, tenant_id = db_tenant
        tenant_id_str = str(tenant_id)

        stmt = select(CandidateStageDict).where(CandidateStageDict.tenant_id == tenant_id_str)
        if active is not None:
            stmt = stmt.where(CandidateStageDict.active == active)

        stmt = stmt.order_by(CandidateStageDict.order, CandidateStageDict.code)

        result = await db.execute(stmt)
        stages = result.scalars().all()

        return [CandidateStageOut.from_model(stage) for stage in stages]
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list candidate stages: {str(e)}",
        )


@router.post("", response_model=CandidateStageOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CandidateStageOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_candidate_stage(
    payload: CandidateStageIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(require_roles(Role.manager, Role.admin)),
):
    """Create a new candidate stage."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    # Check if stage with same code already exists
    existing_stmt = select(CandidateStageDict).where(
        CandidateStageDict.tenant_id == tenant_id_str,
        CandidateStageDict.code == payload.code,
    )
    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage with code '{payload.code}' already exists",
        )

    new_stage = CandidateStageDict(
        tenant_id=tenant_id_str,
        code=payload.code,
        label=payload.label,
        order=payload.order,
        active=payload.active,
    )

    db.add(new_stage)
    await db.commit()
    await db.refresh(new_stage)

    return CandidateStageOut.from_model(new_stage)


@router.get("/{stage_id}", response_model=CandidateStageOut)
async def get_candidate_stage(
    stage_id: int,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(get_current_user),
):
    """Get a candidate stage by ID."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    stmt = select(CandidateStageDict).where(
        CandidateStageDict.id == stage_id,
        CandidateStageDict.tenant_id == tenant_id_str,
    )
    result = await db.execute(stmt)
    stage = result.scalar_one_or_none()

    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found")

    return CandidateStageOut.from_model(stage)


@router.patch("/{stage_id}", response_model=CandidateStageOut)
async def update_candidate_stage(
    stage_id: int,
    payload: CandidateStageIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(require_roles(Role.manager, Role.admin)),
):
    """Update a candidate stage."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    stmt = select(CandidateStageDict).where(
        CandidateStageDict.id == stage_id,
        CandidateStageDict.tenant_id == tenant_id_str,
    )
    result = await db.execute(stmt)
    stage = result.scalar_one_or_none()

    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found")

    # Check if code is being changed and if new code already exists
    if payload.code != stage.code:
        existing_stmt = select(CandidateStageDict).where(
            CandidateStageDict.tenant_id == tenant_id_str,
            CandidateStageDict.code == payload.code,
            CandidateStageDict.id != stage_id,
        )
        existing = await db.execute(existing_stmt)
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stage with code '{payload.code}' already exists",
            )

    stage.code = payload.code
    stage.label = payload.label
    stage.order = payload.order
    stage.active = payload.active

    await db.commit()
    await db.refresh(stage)

    return CandidateStageOut.from_model(stage)


@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_candidate_stage(
    stage_id: int,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user=Depends(require_roles(Role.admin)),
):
    """Delete a candidate stage."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    stmt = select(CandidateStageDict).where(
        CandidateStageDict.id == stage_id,
        CandidateStageDict.tenant_id == tenant_id_str,
    )
    result = await db.execute(stmt)
    stage = result.scalar_one_or_none()

    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found")

    await db.execute(delete(CandidateStageDict).where(CandidateStageDict.id == stage_id))
    await db.commit()

    return None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
