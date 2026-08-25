from __future__ import annotations

from backend.app.constants.stages_adapter import DEFAULT_STAGE_CODE
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Any, Optional, Union

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user_optional
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.db.deps import get_db
from backend.app.services.stage_meta_recruitment_filter import apply_handoff_stage_meta_for_user

# Основные константы стадий. Если модуль отсутствует или в нём иные имена —
# ниже есть безопасные дефолты, чтобы приложение поднималось без падения.
try:  # pragma: no cover - защитный импорт
    from backend.app.constants.stages import (  # type: ignore
        KANBAN_COLUMN_OF as KANBAN_COLUMN_OF_CONST,
        LABELS as LABELS_CONST,
        ORDER as ORDER_CONST,
        STAGES_BY_GROUP as STAGES_BY_GROUP_CONST,
        STATUS_REASON_CHOICES as STATUS_REASON_CHOICES_CONST,
        STAGE_META as STAGE_META_CONST,
    )
except Exception:  # pragma: no cover
    STAGES_BY_GROUP: dict[str, list[str]] = {}
    LABELS: dict[str, str] = {}
    KANBAN_COLUMN_OF: dict[str, str] = {}
    ORDER: list[str] = []
    STATUS_REASON_CHOICES: dict[str, list[dict[str, str]]] = {}
    STAGE_META: dict[str, dict[str, Any]] = {}

# Assign imported constants to expected names if they exist
if 'STAGES_BY_GROUP_CONST' in locals():
    STAGES_BY_GROUP = STAGES_BY_GROUP_CONST
    LABELS = LABELS_CONST
    KANBAN_COLUMN_OF = KANBAN_COLUMN_OF_CONST
    ORDER = ORDER_CONST
    STATUS_REASON_CHOICES = STATUS_REASON_CHOICES_CONST
    STAGE_META = STAGE_META_CONST

# Каталоги для форм (безопасный импорт с дефолтами)

CatalogType = Union[list[dict[str, Any]], list[str], dict[str, Any]]

try:  # pragma: no cover - защитный импорт
    from backend.app.constants import catalogs as CATALOGS  # type: ignore
except Exception:  # pragma: no cover
    CATALOGS = None  # type: ignore

COUNTRIES: CatalogType = getattr(CATALOGS, "COUNTRIES", [])
LANGUAGES: CatalogType = getattr(CATALOGS, "LANGUAGES", [])
DIAL_CODES: CatalogType = getattr(CATALOGS, "DIAL_CODES", [])
MANAGERS: CatalogType = getattr(CATALOGS, "MANAGERS", [])


router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/stages")
async def stages_meta(
    db: AsyncSession = Depends(get_db),
    tenant_id_header: Optional[str] = Header(None, alias="X-Tenant-Id"),
    company_id: Optional[str] = Query(
        None,
        description="Operating company scope for recruitment funnel stages (module-owned pipelines P0)",
    ),
    pipeline_type: str = Query(
        "candidate",
        pattern="^(candidate|lead|employee)$",
        description="Pipeline type for funnel resolution (recruitment candidate/lead or HR employee)",
    ),
    current_user: Optional[UserCtx] = Depends(get_current_user_optional),
):
    """
    Справочник стадий:
    - default: код стадии по умолчанию
    - codes: список всех кодов в порядке групп (включая пользовательские)
    - labels: код -> метка (включая пользовательские)
    - groups: группа-канбан -> список кодов
    - column_of: код -> колонка канбана
    - order: явный порядок кодов (включая пользовательские)
    - reason_choices: варианты причин для статусов
    - custom_stages: список пользовательских этапов (если есть tenant)
    - funnel_id: id воронки, если используется funnel-based stages
    """
    # Anonymous callers may only see system defaults. Tenant funnel/custom stages
    # require an authenticated principal with membership for X-Tenant-Id.
    effective_tenant_header = (tenant_id_header or "").strip() or None
    if effective_tenant_header:
        if current_user is None or not getattr(current_user, "sub", None):
            effective_tenant_header = None
        else:
            try:
                _tid = UUID(effective_tenant_header)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="X-Tenant-Id must be a valid UUID") from exc
            await ensure_user_can_access_tenant(db, current_user, str(_tid))
    tenant_id_header = effective_tenant_header

    # Start with system stages
    merged_labels = dict(LABELS)
    merged_order = list(ORDER)
    custom_stages: list[dict[str, Any]] = []
    funnel_id_out: Optional[str] = None

    # If we have a tenant, try funnel-based stages first
    if tenant_id_header:
        try:
            tenant_id = UUID(tenant_id_header.strip())
            tenant_id_str = str(tenant_id)

            from backend.app.models.funnel import Funnel, FunnelStage

            if pipeline_type == "employee":
                from backend.app.constants.funnel_types import HR_MODULE_KEY
                from backend.app.services.hr_employee_funnel_resolver import (
                    HrEmployeeFunnelNotFoundError,
                    HrModuleNotEnabledError,
                    resolve_hr_employee_funnel,
                )

                if not company_id or not str(company_id).strip():
                    raise HTTPException(
                        status_code=422,
                        detail="company_id is required for pipeline_type=employee",
                    )
                try:
                    resolved = await resolve_hr_employee_funnel(
                        db,
                        tenant_id=tenant_id_str,
                        company_id=str(company_id).strip(),
                    )
                    funnel = resolved.funnel
                except HrModuleNotEnabledError as exc:
                    raise HTTPException(status_code=403, detail=str(exc)) from exc
                except HrEmployeeFunnelNotFoundError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc

                stages_stmt = (
                    select(FunnelStage)
                    .where(FunnelStage.funnel_id == funnel.id)
                    .order_by(FunnelStage.order, FunnelStage.code)
                )
                funnel_stages = [
                    s
                    for s in (await db.execute(stages_stmt)).scalars().all()
                    if str(getattr(s, "pe_maps_to_module", None) or "").strip() == HR_MODULE_KEY
                    and str(getattr(s, "pe_maps_to_code", None) or "").strip()
                ]
                if not funnel_stages:
                    raise HTTPException(
                        status_code=422,
                        detail="HR employee funnel has no hr.* mapped stages",
                    )
                funnel_id_out = funnel.id
                merged_labels = {}
                merged_order = []
                for s in funnel_stages:
                    merged_labels[s.code] = s.label
                    merged_order.append(s.code)
                custom_stages = [
                    {
                        "code": s.code,
                        "label": s.label,
                        "order": s.order,
                        "id": s.id,
                        "pe_maps_to_module": s.pe_maps_to_module,
                        "pe_maps_to_code": s.pe_maps_to_code,
                    }
                    for s in funnel_stages
                ]
            else:
                from backend.app.services.recruitment_funnel_resolver import (
                    RecruitmentFunnelNotFoundError,
                    RecruitmentModuleNotEnabledError,
                    resolve_recruitment_funnel,
                )

                funnel = None
                if company_id and str(company_id).strip():
                    try:
                        resolved = await resolve_recruitment_funnel(
                            db,
                            tenant_id=tenant_id_str,
                            company_id=str(company_id).strip(),
                            pipeline_type="lead" if pipeline_type == "lead" else "candidate",
                        )
                        funnel = resolved.funnel
                    except RecruitmentModuleNotEnabledError as exc:
                        raise HTTPException(status_code=403, detail=str(exc)) from exc
                    except RecruitmentFunnelNotFoundError as exc:
                        raise HTTPException(status_code=422, detail=str(exc)) from exc
                else:
                    funnel_stmt = (
                        select(Funnel)
                        .where(
                            Funnel.tenant_id.in_([tenant_id_str, "default"]),
                            Funnel.type == "candidate",
                            Funnel.is_default == True,
                        )
                        .order_by(Funnel.tenant_id.desc())  # tenant's own funnel before default
                        .limit(1)
                    )
                    funnel_result = await db.execute(funnel_stmt)
                    funnel = funnel_result.scalar_one_or_none()

                if funnel:
                    stages_stmt = (
                        select(FunnelStage)
                        .where(FunnelStage.funnel_id == funnel.id)
                        .order_by(FunnelStage.order, FunnelStage.code)
                    )
                    stages_result = await db.execute(stages_stmt)
                    funnel_stages = list(stages_result.scalars().all())

                    if funnel_stages:
                        funnel_id_out = funnel.id
                        merged_labels = {}
                        merged_order = []
                        for s in funnel_stages:
                            merged_labels[s.code] = s.label
                            merged_order.append(s.code)
                        custom_stages = [
                            {"code": s.code, "label": s.label, "order": s.order, "id": s.id}
                            for s in funnel_stages
                        ]
        except HTTPException:
            raise
        except (ValueError, Exception):
            pass

    # Fallback: use candidate_stage_dict if no funnel stages (recruitment only)
    if not funnel_id_out and tenant_id_header and pipeline_type != "employee":
        try:
            tenant_id = UUID(tenant_id_header.strip())
            tenant_id_str = str(tenant_id)

            from backend.app.models.candidate_stage import CandidateStageDict

            stmt = select(CandidateStageDict).where(
                CandidateStageDict.tenant_id == tenant_id_str,
                CandidateStageDict.active == True,
            ).order_by(CandidateStageDict.order, CandidateStageDict.code)

            result = await db.execute(stmt)
            custom_stage_list = result.scalars().all()

            for custom_stage in custom_stage_list:
                code = custom_stage.code
                label = custom_stage.label
                order = custom_stage.order
                merged_labels[code] = label
                if code not in merged_order:
                    merged_order.append(code)
                custom_stages.append({
                    "code": code,
                    "label": label,
                    "order": order,
                    "id": custom_stage.id,
                })
        except (ValueError, Exception):
            pass

    codes: list[str] = []
    for _, codes_in_group in STAGES_BY_GROUP.items():
        codes.extend(codes_in_group)

    if not codes and merged_order:
        codes = list(merged_order)
    elif merged_order and not funnel_id_out:
        system_codes_set = set(codes)
        custom_codes = [code for code in merged_order if code not in system_codes_set]
        codes = codes + custom_codes
    elif funnel_id_out and merged_order:
        codes = list(merged_order)

    default_code = DEFAULT_STAGE_CODE
    if funnel_id_out and merged_order:
        default_code = merged_order[0]

    # Build per-stage metadata with безопасные дефолты
    stage_meta: dict[str, dict[str, Any]] = {}
    # используем codes (если он пустой, fallback на merged_order)
    meta_source_codes = codes or list(merged_order)
    for code in meta_source_codes:
        base = {
            "is_system": False,
            "visible_for_agency": True,
            "visible_for_client": False,
            "owner": "agency",
        }
        overrides = STAGE_META.get(code) or {}
        merged_meta = {**base, **overrides}
        stage_meta[code] = merged_meta

    out: dict[str, Any] = {
        "default": default_code,
        "codes": codes,
        "labels": merged_labels,
        "groups": STAGES_BY_GROUP,
        "column_of": KANBAN_COLUMN_OF,
        "order": merged_order,
        "reason_choices": STATUS_REASON_CHOICES,
        "custom_stages": custom_stages,
        "meta": stage_meta,
    }
    if funnel_id_out:
        out["funnel_id"] = funnel_id_out
    if pipeline_type == "employee":
        out["pipeline_type"] = "employee"
    tid = (tenant_id_header or "").strip()
    if tid and current_user is not None and pipeline_type != "employee":
        out = await apply_handoff_stage_meta_for_user(db, tid, current_user, out)
    return out


@router.get(
    "/recruitment-funnel-metrics",
    dependencies=[Depends(require_trust_admin())],
)
async def get_recruitment_funnel_metrics() -> dict[str, int | dict[str, int]]:
    """In-process resolver usage counters (legacy fallback deprecation telemetry)."""
    from backend.app.services.recruitment_funnel_metrics import (
        get_recruitment_funnel_metrics_snapshot,
    )

    return get_recruitment_funnel_metrics_snapshot().to_dict()


# --- Catalogs API ---
catalogs_router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@catalogs_router.get("/countries")
async def get_countries():
    return COUNTRIES


@catalogs_router.get("/languages")
async def get_languages():
    return LANGUAGES


@catalogs_router.get("/dial-codes")
async def get_dial_codes():
    return DIAL_CODES


@catalogs_router.get("/managers")
async def get_managers():
    return MANAGERS
