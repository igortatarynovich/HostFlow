"""API for universal Funnel model (candidate, lead, deal pipelines)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.user import Role
from backend.app.services.plan_feature_gates import ensure_custom_funnel_create_allowed

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

# §2.12 conversion funnel roots (lead funnels only; stored on funnel_stages.conversion_root_v1).
CONVERSION_ROOT_LEAD_VALUES = frozenset({"lead", "qualified", "active", "final"})


def _infer_conversion_root_v1_from_lead_code(code: str) -> Optional[str]:
    c = (code or "").strip().lower()
    if c == "new":
        return "lead"
    if c == "contacted":
        return "qualified"
    if c == "qualified":
        return "active"
    if c == "converted":
        return "final"
    return None


def _resolve_conversion_root_v1_db(
    funnel_type: str,
    *,
    code: str,
    payload_value: Optional[str],
    field_was_set: bool,
) -> Optional[str]:
    if funnel_type != "lead":
        if field_was_set and (payload_value is not None and str(payload_value).strip() != ""):
            raise HTTPException(
                status_code=422,
                detail="conversion_root_v1 is only supported for funnels with type=lead",
            )
        return None
    if not field_was_set:
        return _infer_conversion_root_v1_from_lead_code(code)
    raw = payload_value
    if raw is None or not str(raw).strip():
        return None
    v = str(raw).strip().lower()
    if v not in CONVERSION_ROOT_LEAD_VALUES:
        raise HTTPException(
            status_code=422,
            detail="conversion_root_v1 must be one of: lead, qualified, active, final",
        )
    return v


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


class StageContractV1(BaseModel):
    """Per-stage pipeline contract (§2.3): optional until UI/engine consume it."""

    model_config = ConfigDict(extra="forbid")

    owner_role: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Intended owner role for work in this stage (e.g. recruiter, manager).",
    )
    required_actions: Optional[List[str]] = Field(
        default=None,
        description="Human-readable required actions before leaving the stage.",
    )
    sla_hours: Optional[int] = Field(
        default=None,
        ge=0,
        le=8760,
        description="Optional SLA window in hours for this stage.",
    )
    auto_rules: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Opaque JSON for future automation links (e.g. rule ids, triggers).",
    )

    @field_validator("required_actions")
    @classmethod
    def _normalize_actions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return None
        out = [str(x).strip() for x in v if str(x).strip()]
        if not out:
            return None
        return out[:48]

    @field_validator("owner_role")
    @classmethod
    def _strip_owner(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


def _stage_contract_db_value(payload: Optional[StageContractV1]) -> Optional[dict[str, Any]]:
    if payload is None:
        return None
    dumped = payload.model_dump(exclude_none=True)
    return dumped if dumped else None


class FunnelStageIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=255)
    system_stage: Optional[str] = Field(
        default=None,
        description="System skeleton stage: new | in_progress | hired | declined_rejected",
    )
    order: int = Field(0, ge=0)
    is_terminal: bool = False
    conversion_root_v1: Optional[str] = Field(
        default=None,
        description="Lead funnels only: §2.12 root bucket (lead | qualified | active | final). Omit to infer from code.",
    )
    stage_contract: Optional[StageContractV1] = Field(
        default=None,
        description="Optional pipeline contract (owner_role, required_actions, sla_hours, auto_rules).",
    )


class FunnelStageOut(BaseModel):
    id: str
    funnel_id: str
    code: str
    label: str
    system_stage: str
    order: int
    is_terminal: bool
    conversion_root_v1: Optional[str] = None
    stage_contract: Optional[StageContractV1] = None

    @classmethod
    def from_model(cls, s: FunnelStage) -> "FunnelStageOut":
        raw = getattr(s, "stage_contract_v1", None)
        contract: Optional[StageContractV1] = None
        if isinstance(raw, dict) and raw:
            try:
                contract = StageContractV1.model_validate(raw)
            except Exception:
                contract = None
        cr = getattr(s, "conversion_root_v1", None)
        cr_out = str(cr).strip() if cr else None
        return cls(
            id=s.id,
            funnel_id=s.funnel_id,
            code=s.code,
            label=s.label,
            system_stage=s.system_stage,
            order=s.order,
            is_terminal=s.is_terminal,
            conversion_root_v1=cr_out,
            stage_contract=contract,
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

    await ensure_custom_funnel_create_allowed(db, tenant_str)

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
    cr_db = _resolve_conversion_root_v1_db(
        str(funnel.type),
        code=payload.code,
        payload_value=payload.conversion_root_v1,
        field_was_set="conversion_root_v1" in payload.model_fields_set,
    )
    stage_kwargs: dict[str, Any] = dict(
        id=str(uuid.uuid4()),
        funnel_id=funnel_id,
        code=payload.code,
        label=payload.label,
        system_stage=resolved_system_stage,
        order=payload.order,
        is_terminal=payload.is_terminal
        or resolved_system_stage in {SYSTEM_STAGE_HIRED, SYSTEM_STAGE_DECLINED_OR_REJECTED},
        conversion_root_v1=cr_db,
    )
    if "stage_contract" in payload.model_fields_set:
        stage_kwargs["stage_contract_v1"] = _stage_contract_db_value(payload.stage_contract)
    stage = FunnelStage(**stage_kwargs)
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

    funnel_row = (
        await db.execute(
            select(Funnel).where(
                Funnel.id == funnel_id,
                Funnel.tenant_id == tenant_str,
            )
        )
    ).scalar_one_or_none()
    if not funnel_row:
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
    if "conversion_root_v1" in payload.model_fields_set:
        stage.conversion_root_v1 = _resolve_conversion_root_v1_db(
            str(funnel_row.type),
            code=payload.code,
            payload_value=payload.conversion_root_v1,
            field_was_set=True,
        )
    if "stage_contract" in payload.model_fields_set:
        stage.stage_contract_v1 = _stage_contract_db_value(payload.stage_contract)
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
