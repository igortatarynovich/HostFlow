"""API for universal Funnel model (candidate, lead, deal pipelines)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.auth.deps import UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage, FunnelTransitionEdge
from backend.app.constants.system_transitions import (
    ALL_CATALOG_KEYS,
    available_transitions,
    get_transition,
    is_forbidden_operational_stage,
)
from backend.app.models.lead import Lead
from backend.app.models.tenant import Tenant
from backend.app.models.user import Role
from backend.app.models.vacancy import Vacancy
from backend.app.services import billing_restrictions, company_module_settings_service as cms_svc
from backend.app.services.company_module_access import company_allows_module
from backend.app.constants.funnel_types import (
    FUNNEL_TYPE_PATTERN,
    HR_EMPLOYEE_FUNNEL_TYPE,
    PLATFORM_SEED_TENANT_ID,
    RECRUITMENT_MODULE_KEY,
    is_hr_employee_funnel_type,
)
from backend.app.services.plan_feature_gates import ensure_custom_funnel_create_allowed

router = APIRouter(prefix="/funnels", tags=["funnels"])


async def _load_transitions(db: AsyncSession, funnel_id: str) -> list[FunnelTransitionEdge]:
    res = await db.execute(
        select(FunnelTransitionEdge)
        .where(FunnelTransitionEdge.funnel_id == funnel_id)
        .order_by(FunnelTransitionEdge.order)
    )
    return list(res.scalars().all())


async def _enforce_company_module_scope(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    module_key: str,
    current_user: UserCtx,
) -> tuple[Tenant, Company]:
    cid = str(company_id or "").strip()
    if not cid:
        raise HTTPException(status_code=422, detail="company_id is required")

    mk = str(module_key or "").strip()
    if mk not in {RECRUITMENT_MODULE_KEY, HR_MODULE_KEY}:
        raise HTTPException(status_code=422, detail=f"unsupported module_key {module_key!r}")

    company = await cms_svc.get_company_for_tenant(db, tenant_id, cid)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    acl = await resolve_restricted_acl(db, tenant_id, current_user)
    if acl is not None and acl.company_ids and cid not in acl.company_ids:
        raise HTTPException(status_code=403, detail="Forbidden")

    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not company_allows_module(tenant, company, mk):
        raise HTTPException(
            status_code=403,
            detail=f"{mk} module is not enabled for this company",
        )
    return tenant, company


async def _enforce_company_recruitment_scope(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    current_user: UserCtx,
) -> tuple[Tenant, Company]:
    return await _enforce_company_module_scope(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        module_key=RECRUITMENT_MODULE_KEY,
        current_user=current_user,
    )


def _funnel_owner_module_key(funnel: Funnel) -> str:
    module = str(getattr(funnel, "module_key", None) or "").strip()
    if module in {RECRUITMENT_MODULE_KEY, HR_MODULE_KEY}:
        return module
    return RECRUITMENT_MODULE_KEY


def _ensure_funnel_mutable_for_module(funnel: Funnel, *, module_key: str) -> None:
    if not str(getattr(funnel, "company_id", None) or "").strip():
        raise HTTPException(
            status_code=403,
            detail=(
                "Legacy tenant-wide funnels are read-only (strangler). "
                "Create company-scoped funnels instead."
            ),
        )
    owner = _funnel_owner_module_key(funnel)
    if owner != str(module_key).strip():
        raise HTTPException(
            status_code=403,
            detail=f"Funnel is owned by module {owner}, not {module_key}",
        )


def _ensure_funnel_mutable(funnel: Funnel) -> None:
    _ensure_funnel_mutable_for_module(funnel, module_key=_funnel_owner_module_key(funnel))


async def _enforce_funnel_module_access(
    db: AsyncSession,
    *,
    funnel: Funnel,
    tenant_id: str,
    current_user: UserCtx,
) -> None:
    company_str = str(getattr(funnel, "company_id", None) or "").strip()
    if not company_str:
        _ensure_funnel_mutable(funnel)
        return
    module_key = _funnel_owner_module_key(funnel)
    _ensure_funnel_mutable_for_module(funnel, module_key=module_key)
    await _enforce_company_module_scope(
        db,
        tenant_id=tenant_id,
        company_id=company_str,
        module_key=module_key,
        current_user=current_user,
    )


def _validate_list_module_type(module_key: str, type_filter: Optional[str]) -> None:
    mk = str(module_key or "").strip()
    tf = str(type_filter or "").strip()
    if mk == HR_MODULE_KEY:
        if tf and tf != HR_EMPLOYEE_FUNNEL_TYPE:
            raise HTTPException(
                status_code=422,
                detail="module_key=hr only supports type=employee",
            )
    elif tf == HR_EMPLOYEE_FUNNEL_TYPE:
        raise HTTPException(
            status_code=422,
            detail="type=employee requires module_key=hr",
        )


async def _load_funnel_for_tenant(
    db: AsyncSession,
    *,
    funnel_id: str,
    tenant_str: str,
) -> Optional[Funnel]:
    result = await db.execute(
        select(Funnel).where(
            Funnel.id == funnel_id,
            Funnel.tenant_id.in_([tenant_str, PLATFORM_SEED_TENANT_ID]),
        )
    )
    return result.scalar_one_or_none()

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


async def _require_candidate_funnel_pe_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel: Funnel,
    stage: FunnelStage,
) -> None:
    """P4: candidate funnel stages must map to a registered Process Engine system stage."""
    if str(getattr(funnel, "type", "") or "") != "candidate":
        return

    from backend.app.process_engine.pipeline_mapping import (
        ensure_funnel_stage_pe_mapping,
        infer_pe_mapping,
        validate_pe_system_stage,
    )

    await ensure_funnel_stage_pe_mapping(db, stage, tenant_id=tenant_id)
    pe_module = str(getattr(stage, "pe_maps_to_module", None) or "").strip()
    pe_code = str(getattr(stage, "pe_maps_to_code", None) or "").strip()
    if pe_module and pe_code:
        if not await validate_pe_system_stage(
            db, tenant_id=tenant_id, module=pe_module, code=pe_code
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Process Engine system stage '{pe_module}.{pe_code}' is not registered",
            )
        return

    inferred = infer_pe_mapping(str(stage.code or ""))
    if inferred is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Stage code '{stage.code}' has no valid Process Engine system stage mapping. "
                "Choose a supported recruitment stage code or register the system stage first."
            ),
        )
    mod, code = inferred
    if not await validate_pe_system_stage(db, tenant_id=tenant_id, module=mod, code=code):
        raise HTTPException(
            status_code=422,
            detail=f"Process Engine system stage '{mod}.{code}' is not registered for this tenant",
        )
    stage.pe_maps_to_module = mod
    stage.pe_maps_to_code = code


async def _require_hr_employee_funnel_pe_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel: Funnel,
    stage: FunnelStage,
) -> None:
    """HR employee funnel stages must map to registered hr.* Process Engine codes."""
    if str(getattr(funnel, "type", "") or "") != HR_EMPLOYEE_FUNNEL_TYPE:
        return

    from backend.app.process_engine.constants import HR_MODULE
    from backend.app.process_engine.pipeline_mapping import (
        apply_pe_mapping_to_funnel_stage,
        validate_pe_system_stage,
    )

    pe_code = str(stage.code or "").strip()
    if not pe_code:
        raise HTTPException(status_code=422, detail="HR employee stage code is required")
    if not await validate_pe_system_stage(
        db, tenant_id=tenant_id, module=HR_MODULE, code=pe_code
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Process Engine system stage 'hr.{pe_code}' is not registered for this tenant",
        )
    await apply_pe_mapping_to_funnel_stage(
        db,
        stage,
        tenant_id=tenant_id,
        module=HR_MODULE,
        code=pe_code,
        source="pipeline_template",
    )


async def _require_funnel_stage_pe_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel: Funnel,
    stage: FunnelStage,
) -> None:
    if is_hr_employee_funnel_type(str(getattr(funnel, "type", "") or "")):
        await _require_hr_employee_funnel_pe_mapping(
            db, tenant_id=tenant_id, funnel=funnel, stage=stage
        )
        return
    await _require_candidate_funnel_pe_mapping(
        db, tenant_id=tenant_id, funnel=funnel, stage=stage
    )


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
    company_id: str = Field(..., min_length=1, max_length=36)
    type: str = Field(..., pattern=FUNNEL_TYPE_PATTERN)
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False


class FunnelPatchIn(BaseModel):
    type: str = Field(..., pattern=FUNNEL_TYPE_PATTERN)
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False


class FunnelTransitionOut(BaseModel):
    id: str
    funnel_id: str
    catalog_key: str
    label: str
    from_stage_id: Optional[str] = None
    order: int = 0
    config_json: Optional[Dict[str, Any]] = None
    locks_semantics: bool = True

    @classmethod
    def from_model(cls, e: FunnelTransitionEdge) -> "FunnelTransitionOut":
        tdef = get_transition(e.catalog_key)
        return cls(
            id=e.id,
            funnel_id=e.funnel_id,
            catalog_key=e.catalog_key,
            label=(tdef.label if tdef else e.catalog_key),
            from_stage_id=e.from_stage_id,
            order=int(e.order or 0),
            config_json=e.config_json if isinstance(e.config_json, dict) else None,
            locks_semantics=True,
        )


class FunnelTransitionIn(BaseModel):
    catalog_key: str = Field(..., min_length=1, max_length=64)
    from_stage_id: Optional[str] = None
    order: int = Field(0, ge=0)
    config_json: Optional[Dict[str, Any]] = None


class SystemTransitionCatalogItem(BaseModel):
    key: str
    label: str
    source_module: str
    source_object_type: str
    target_module: Optional[str] = None
    target_object_type: Optional[str] = None
    requires_enabled_module: Optional[str] = None
    locks_semantics: bool = True


class FunnelOut(BaseModel):
    id: str
    tenant_id: str
    company_id: Optional[str] = None
    module_key: Optional[str] = None
    type: str
    name: str
    is_default: bool
    is_legacy_readonly: bool = False
    template_key: Optional[str] = None
    stages: List[FunnelStageOut] = []
    transitions: List[FunnelTransitionOut] = []

    @classmethod
    def from_model(
        cls,
        f: Funnel,
        stages: Optional[List[FunnelStage]] = None,
        transitions: Optional[List[FunnelTransitionEdge]] = None,
    ) -> "FunnelOut":
        stage_list = stages if stages is not None else list(f.stages) if hasattr(f, "stages") else []
        edge_list = (
            transitions
            if transitions is not None
            else (list(f.transitions) if hasattr(f, "transitions") else [])
        )
        company_id = str(f.company_id).strip() if getattr(f, "company_id", None) else None
        module_key = str(f.module_key).strip() if getattr(f, "module_key", None) else None
        template_key = str(f.template_key).strip() if getattr(f, "template_key", None) else None
        return cls(
            id=f.id,
            tenant_id=f.tenant_id,
            company_id=company_id or None,
            module_key=module_key or None,
            type=f.type,
            name=f.name,
            is_default=f.is_default,
            is_legacy_readonly=not bool(company_id),
            template_key=template_key or None,
            stages=[FunnelStageOut.from_model(s) for s in stage_list],
            transitions=[FunnelTransitionOut.from_model(e) for e in edge_list],
        )


@router.get("", response_model=List[FunnelOut])
@router.get("/", response_model=List[FunnelOut], include_in_schema=False)
async def list_funnels(
    company_id: str = Query(..., min_length=1, max_length=36),
    type_filter: Optional[str] = Query(None, alias="type"),
    module_key: str = Query(RECRUITMENT_MODULE_KEY, min_length=1, max_length=32),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> List[FunnelOut]:
    """List company-scoped operational funnels (excludes legacy tenant-wide rows)."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    company_str = str(company_id).strip()
    module_str = str(module_key).strip()
    if module_str not in {RECRUITMENT_MODULE_KEY, HR_MODULE_KEY}:
        raise HTTPException(status_code=422, detail=f"unsupported module_key {module_key!r}")
    _validate_list_module_type(module_str, type_filter)

    await _enforce_company_module_scope(
        db,
        tenant_id=tenant_str,
        company_id=company_str,
        module_key=module_str,
        current_user=current_user,
    )

    stmt = (
        select(Funnel)
        .where(
            Funnel.tenant_id == tenant_str,
            Funnel.company_id == company_str,
            Funnel.module_key == module_str,
        )
    )
    if type_filter:
        stmt = stmt.where(Funnel.type == type_filter)
    elif module_str == HR_MODULE_KEY:
        stmt = stmt.where(Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE)
    stmt = stmt.order_by(Funnel.is_default.desc(), Funnel.name)
    result = await db.execute(stmt)
    funnels = result.scalars().all()

    out: List[FunnelOut] = []
    for f in funnels:
        stages_stmt = select(FunnelStage).where(FunnelStage.funnel_id == f.id).order_by(FunnelStage.order)
        stages_result = await db.execute(stages_stmt)
        stages = list(stages_result.scalars().all())
        edges = await _load_transitions(db, f.id)
        out.append(FunnelOut.from_model(f, stages, edges))
    return out


@router.get("/meta/system-transitions", response_model=List[SystemTransitionCatalogItem])
async def list_system_transition_catalog(
    source_module: str = Query(..., min_length=1),
    source_object_type: str = Query(..., min_length=1),
    enabled_modules: Optional[str] = Query(
        None,
        description="Comma-separated company enabled module keys (e.g. hr,fleet)",
    ),
    current_user: UserCtx = Depends(get_current_user),
) -> List[SystemTransitionCatalogItem]:
    """ADR-035 A2: platform catalog filtered by source + enabled modules."""
    _ = current_user
    enabled = [p.strip() for p in str(enabled_modules or "").split(",") if p.strip()]
    items = available_transitions(
        source_module=source_module,
        source_object_type=source_object_type,
        enabled_modules=enabled,
    )
    return [
        SystemTransitionCatalogItem(
            key=t.key,
            label=t.label,
            source_module=t.source_module,
            source_object_type=t.source_object_type,
            target_module=t.target_module,
            target_object_type=t.target_object_type,
            requires_enabled_module=t.requires_enabled_module,
            locks_semantics=t.locks_semantics,
        )
        for t in items
    ]


@router.get("/{funnel_id}", response_model=FunnelOut)
async def get_funnel(
    funnel_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> FunnelOut:
    """Get funnel with stages (legacy/platform rows are read-only strangler)."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    funnel = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")

    funnel_company = str(getattr(funnel, "company_id", None) or "").strip() or None
    if funnel_company:
        await _enforce_funnel_module_access(
            db,
            funnel=funnel,
            tenant_id=tenant_str,
            current_user=current_user,
        )

    stages_result = await db.execute(
        select(FunnelStage).where(FunnelStage.funnel_id == funnel.id).order_by(FunnelStage.order)
    )
    stages = list(stages_result.scalars().all())
    edges = await _load_transitions(db, funnel.id)
    return FunnelOut.from_model(funnel, stages, edges)


@router.post("", response_model=FunnelOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FunnelOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_funnel(
    payload: FunnelIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.manager, Role.admin, Role.hr_officer)),
) -> FunnelOut:
    """Create a company-scoped operational funnel (recruitment or HR employee)."""
    import uuid

    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    company_str = str(payload.company_id).strip()

    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_str)
    await ensure_custom_funnel_create_allowed(db, tenant_str)

    if is_hr_employee_funnel_type(payload.type):
        await _enforce_company_module_scope(
            db,
            tenant_id=tenant_str,
            company_id=company_str,
            module_key=HR_MODULE_KEY,
            current_user=current_user,
        )
        if payload.is_default:
            existing = await db.execute(
                select(Funnel).where(
                    Funnel.tenant_id == tenant_str,
                    Funnel.company_id == company_str,
                    Funnel.module_key == HR_MODULE_KEY,
                    Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
                )
            )
            for f in existing.scalars().all():
                f.is_default = False
        funnel = Funnel(
            id=str(uuid.uuid4()),
            tenant_id=tenant_str,
            company_id=company_str,
            module_key=HR_MODULE_KEY,
            type=HR_EMPLOYEE_FUNNEL_TYPE,
            name=payload.name,
            is_default=payload.is_default,
        )
        db.add(funnel)
        await db.commit()
        await db.refresh(funnel)
        return FunnelOut.from_model(funnel, [])

    await _enforce_company_recruitment_scope(
        db,
        tenant_id=tenant_str,
        company_id=company_str,
        current_user=current_user,
    )

    if payload.is_default:
        unset_stmt = select(Funnel).where(
            Funnel.tenant_id == tenant_str,
            Funnel.company_id == company_str,
            Funnel.module_key == RECRUITMENT_MODULE_KEY,
            Funnel.type == payload.type,
        )
        existing = await db.execute(unset_stmt)
        for f in existing.scalars().all():
            f.is_default = False

    funnel = Funnel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_str,
        company_id=company_str,
        module_key=RECRUITMENT_MODULE_KEY,
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
    payload: FunnelPatchIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelOut:
    """Update a company-scoped funnel."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_str)
    funnel = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel or funnel.tenant_id != tenant_str:
        raise HTTPException(status_code=404, detail="Funnel not found")

    _ensure_funnel_mutable(funnel)
    await _enforce_funnel_module_access(
        db,
        funnel=funnel,
        tenant_id=tenant_str,
        current_user=current_user,
    )

    owner_module = _funnel_owner_module_key(funnel)
    if owner_module == HR_MODULE_KEY and not is_hr_employee_funnel_type(payload.type):
        raise HTTPException(
            status_code=422,
            detail="HR funnels only support type=employee",
        )
    if owner_module == RECRUITMENT_MODULE_KEY and is_hr_employee_funnel_type(payload.type):
        raise HTTPException(
            status_code=422,
            detail="Recruitment funnels cannot use type=employee",
        )

    company_str = str(funnel.company_id or "").strip()
    if payload.is_default and not funnel.is_default:
        unset = await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_str,
                Funnel.company_id == company_str,
                Funnel.module_key == owner_module,
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
    edges = await _load_transitions(db, funnel.id)
    return FunnelOut.from_model(funnel, list(stages_result.scalars().all()), edges)


@router.post("/{funnel_id}/stages", response_model=FunnelStageOut, status_code=status.HTTP_201_CREATED)
async def add_funnel_stage(
    funnel_id: str,
    payload: FunnelStageIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelStageOut:
    """Add stage to funnel."""
    import uuid

    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_str)
    funnel = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel or funnel.tenant_id != tenant_str:
        raise HTTPException(status_code=404, detail="Funnel not found")

    _ensure_funnel_mutable(funnel)
    await _enforce_funnel_module_access(
        db,
        funnel=funnel,
        tenant_id=tenant_str,
        current_user=current_user,
    )

    existing = await db.execute(
        select(FunnelStage).where(
            FunnelStage.funnel_id == funnel_id,
            FunnelStage.code == payload.code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Stage code '{payload.code}' already exists")

    if is_forbidden_operational_stage(payload.code):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Stage code '{payload.code}' is a legacy handoff pseudo-stage and cannot be an "
                "operational board column (ADR-035). Add a system transition instead."
            ),
        )

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
    await _require_funnel_stage_pe_mapping(
        db, tenant_id=tenant_str, funnel=funnel, stage=stage
    )
    await db.commit()
    await db.refresh(stage)
    return FunnelStageOut.from_model(stage)


@router.patch("/{funnel_id}/stages/{stage_id}", response_model=FunnelStageOut)
async def update_funnel_stage(
    funnel_id: str,
    stage_id: str,
    payload: FunnelStageIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelStageOut:
    """Update funnel stage."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_str)
    funnel_row = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel_row or funnel_row.tenant_id != tenant_str:
        raise HTTPException(status_code=404, detail="Funnel not found")

    _ensure_funnel_mutable(funnel_row)
    await _enforce_funnel_module_access(
        db,
        funnel=funnel_row,
        tenant_id=tenant_str,
        current_user=current_user,
    )

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
    await _require_funnel_stage_pe_mapping(
        db, tenant_id=tenant_str, funnel=funnel_row, stage=stage
    )
    await db.commit()
    await db.refresh(stage)
    return FunnelStageOut.from_model(stage)


@router.delete(
    "/{funnel_id}/stages/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_funnel_stage(
    funnel_id: str,
    stage_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.admin)),
) -> None:
    """Delete funnel stage."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_str)
    funnel = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel or funnel.tenant_id != tenant_str:
        raise HTTPException(status_code=404, detail="Funnel not found")

    _ensure_funnel_mutable(funnel)
    await _enforce_funnel_module_access(
        db,
        funnel=funnel,
        tenant_id=tenant_str,
        current_user=current_user,
    )

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


@router.delete(
    "/{funnel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_funnel(
    funnel_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.manager, Role.admin)),
) -> None:
    """Delete a custom funnel when it is not default and not referenced anywhere."""
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)

    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_str)
    funnel = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel or funnel.tenant_id != tenant_str:
        raise HTTPException(status_code=404, detail="Funnel not found")

    _ensure_funnel_mutable(funnel)
    await _enforce_funnel_module_access(
        db,
        funnel=funnel,
        tenant_id=tenant_str,
        current_user=current_user,
    )

    if bool(getattr(funnel, "is_default", False)):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the default funnel. Assign another default funnel first.",
        )

    refs = {
        "candidate profiles": CandidateProfile.funnel_id,
        "candidates": Candidate.funnel_id,
        "leads": Lead.funnel_id,
        "vacancies": Vacancy.funnel_id,
    }
    for label, column in refs.items():
        in_use = (
            await db.execute(select(column).where(column == funnel_id).limit(1))
        ).scalar_one_or_none()
        if in_use is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete funnel: it is still used by {label}.",
            )

    await db.delete(funnel)
    await db.commit()


@router.post(
    "/{funnel_id}/transitions",
    response_model=FunnelTransitionOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_funnel_transition(
    funnel_id: str,
    payload: FunnelTransitionIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.manager, Role.admin)),
) -> FunnelTransitionOut:
    import uuid

    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_str)
    funnel = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    _ensure_funnel_mutable(funnel)
    await _enforce_funnel_module_access(
        db, funnel=funnel, tenant_id=tenant_str, current_user=current_user
    )

    key = str(payload.catalog_key or "").strip()
    if key not in ALL_CATALOG_KEYS:
        raise HTTPException(status_code=422, detail=f"Unknown catalog_key '{key}'")
    tdef = get_transition(key)
    assert tdef is not None

    if funnel.company_id and tdef.requires_enabled_module:
        tenant_obj = await db.get(Tenant, tenant_str)
        company_obj = await db.get(Company, str(funnel.company_id))
        if tenant_obj and company_obj:
            if not company_allows_module(
                tenant_obj, company_obj, tdef.requires_enabled_module
            ):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Transition '{key}' requires module "
                        f"'{tdef.requires_enabled_module}' enabled for company"
                    ),
                )

    edge = FunnelTransitionEdge(
        id=str(uuid.uuid4()),
        funnel_id=funnel_id,
        catalog_key=key,
        from_stage_id=payload.from_stage_id,
        order=payload.order,
        config_json=payload.config_json,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return FunnelTransitionOut.from_model(edge)


@router.delete(
    "/{funnel_id}/transitions/{transition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_funnel_transition(
    funnel_id: str,
    transition_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(require_roles(Role.manager, Role.admin)),
) -> Response:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    funnel = await _load_funnel_for_tenant(db, funnel_id=funnel_id, tenant_str=tenant_str)
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    _ensure_funnel_mutable(funnel)
    await _enforce_funnel_module_access(
        db, funnel=funnel, tenant_id=tenant_str, current_user=current_user
    )
    res = await db.execute(
        select(FunnelTransitionEdge).where(
            FunnelTransitionEdge.id == transition_id,
            FunnelTransitionEdge.funnel_id == funnel_id,
        )
    )
    edge = res.scalar_one_or_none()
    if not edge:
        raise HTTPException(status_code=404, detail="Transition not found")
    await db.delete(edge)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
