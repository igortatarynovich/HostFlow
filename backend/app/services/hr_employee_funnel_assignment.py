"""HR employee funnel runtime assignment (hr-employee-pipeline-p0 H4)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.funnel_types import HR_MODULE_KEY
from backend.app.models.funnel import Funnel
from backend.app.services.hr_employee_funnel_bootstrap import HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES
from backend.app.services.hr_employee_funnel_resolver import (
    HrEmployeeFunnelForbiddenError,
    HrEmployeeFunnelNotFoundError,
    HrEmployeeFunnelResolveResult,
    HrModuleNotEnabledError,
    resolve_hr_employee_funnel,
)


def _http_from_resolve_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HrModuleNotEnabledError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, HrEmployeeFunnelForbiddenError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, HrEmployeeFunnelNotFoundError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))

EMPLOYEE_PIPELINE_META_KEY = "employee_pipeline"
RECRUITMENT_HANDOFF_ENTRY_PE_STAGE = "received_from_recruitment"
RECRUITMENT_HANDOFF_PIPELINE_ORIGIN = "recruitment_handoff"


def _funnel_stage_order(funnel: Funnel, stage_code: str) -> Optional[int]:
    code = str(stage_code or "").strip()
    if not code:
        return None
    for stage in list(getattr(funnel, "stages", None) or []):
        if str(getattr(stage, "code", "") or "").strip() == code:
            return int(getattr(stage, "order", 0) or 0)
    return None


def funnel_stage_code_for_pe_system_stage(
    funnel: Funnel,
    *,
    pe_module: str,
    pe_code: str,
) -> Optional[str]:
    module = str(pe_module or "").strip()
    system_stage = str(pe_code or "").strip()
    if not module or not system_stage:
        return None
    for stage in list(getattr(funnel, "stages", None) or []):
        if (
            str(getattr(stage, "pe_maps_to_module", None) or "").strip() == module
            and str(getattr(stage, "pe_maps_to_code", None) or "").strip() == system_stage
        ):
            return str(getattr(stage, "code", "") or "").strip() or None
    return None


def resolve_recruitment_handoff_entry_stage(funnel: Funnel) -> tuple[str, bool]:
    """Map recruitment handoff entry to funnel stage; fallback to first HR intake stage."""
    mapped = funnel_stage_code_for_pe_system_stage(
        funnel,
        pe_module=HR_MODULE_KEY,
        pe_code=RECRUITMENT_HANDOFF_ENTRY_PE_STAGE,
    )
    if mapped:
        return mapped, False
    first = first_hr_employee_funnel_stage_code(funnel)
    if first:
        return first, True
    return HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES[0], True


def _pipeline_stage_update_allowed(
    funnel: Funnel,
    *,
    current_stage_code: str,
    entry_stage_code: str,
) -> bool:
    """§5.3 — do not downgrade pipeline stage on repeat recruitment handoff."""
    current = str(current_stage_code or "").strip()
    if not current:
        return True
    entry_order = _funnel_stage_order(funnel, entry_stage_code)
    current_order = _funnel_stage_order(funnel, current)
    if entry_order is None or current_order is None:
        return False
    return current_order < entry_order


def first_hr_employee_funnel_stage_code(funnel: Funnel) -> Optional[str]:
    """First funnel stage code by order (default pipeline stage on employee create)."""
    stages = list(getattr(funnel, "stages", None) or [])
    if not stages:
        return None
    ordered = sorted(stages, key=lambda s: (int(getattr(s, "order", 0) or 0), str(s.code)))
    for stage in ordered:
        module = str(getattr(stage, "pe_maps_to_module", None) or "").strip()
        code = str(getattr(stage, "pe_maps_to_code", None) or "").strip()
        if module == HR_MODULE_KEY and code:
            return str(stage.code or code).strip() or None
    first = ordered[0]
    return str(getattr(first, "code", "") or "").strip() or None


def _hr_mapped_stage_codes(funnel: Funnel) -> set[str]:
    out: set[str] = set()
    for stage in list(getattr(funnel, "stages", None) or []):
        module = str(getattr(stage, "pe_maps_to_module", None) or "").strip()
        pe_code = str(getattr(stage, "pe_maps_to_code", None) or "").strip()
        stage_code = str(getattr(stage, "code", "") or "").strip()
        if module != HR_MODULE_KEY or not pe_code or not stage_code:
            continue
        out.add(stage_code)
    return out


def default_pipeline_stage_from_result(
    result: HrEmployeeFunnelResolveResult,
    *,
    stage_explicit: bool,
    pipeline_stage: Optional[str],
) -> str:
    if stage_explicit and (pipeline_stage or "").strip():
        return str(pipeline_stage).strip()
    first = first_hr_employee_funnel_stage_code(result.funnel)
    if first:
        return first
    return str(pipeline_stage or "").strip()


async def resolve_hr_employee_funnel_for_workforce(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    explicit_funnel_id: Optional[str] = None,
) -> HrEmployeeFunnelResolveResult:
    """Resolve HR employee pipeline funnel; raises HTTPException on failure."""
    try:
        return await resolve_hr_employee_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            explicit_funnel_id=explicit_funnel_id,
        )
    except (
        HrModuleNotEnabledError,
        HrEmployeeFunnelForbiddenError,
        HrEmployeeFunnelNotFoundError,
    ) as exc:
        raise _http_from_resolve_error(exc) from exc


def _validate_pipeline_stage_for_funnel(funnel: Funnel, pipeline_stage: str) -> str:
    code = str(pipeline_stage or "").strip()
    if not code:
        raise HTTPException(status_code=422, detail="pipeline_stage is empty")
    allowed = _hr_mapped_stage_codes(funnel)
    if code not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"pipeline_stage {code!r} is not a valid HR employee funnel stage",
        )
    return code


async def assign_hr_employee_pipeline_on_create(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    employee_meta: Optional[dict[str, Any]] = None,
    explicit_funnel_id: Optional[str] = None,
    pipeline_stage: Optional[str] = None,
) -> dict[str, Any]:
    """Bind resolved HR employee funnel + stage into ``meta[employee_pipeline]``."""
    company_str = str(company_id or "").strip()
    if not company_str:
        return dict(employee_meta or {})

    stage_explicit = bool(str(pipeline_stage or "").strip())
    result = await resolve_hr_employee_funnel_for_workforce(
        db,
        tenant_id=tenant_id,
        company_id=company_str,
        explicit_funnel_id=explicit_funnel_id,
    )
    stage_code = default_pipeline_stage_from_result(
        result,
        stage_explicit=stage_explicit,
        pipeline_stage=pipeline_stage,
    )
    if stage_explicit:
        stage_code = _validate_pipeline_stage_for_funnel(result.funnel, stage_code)
    elif stage_code:
        stage_code = _validate_pipeline_stage_for_funnel(result.funnel, stage_code)

    meta_out = dict(employee_meta or {})
    meta_out[EMPLOYEE_PIPELINE_META_KEY] = {
        "funnel_id": result.funnel.id,
        "stage_code": stage_code,
        "source": result.source,
    }
    return meta_out


async def assign_hr_employee_pipeline_from_recruitment_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    employee_meta: Optional[dict[str, Any]] = None,
    explicit_funnel_id: Optional[str] = None,
) -> dict[str, Any]:
    """Recruitment handoff materialization: entry stage ``received_from_recruitment`` when mapped."""
    company_str = str(company_id or "").strip()
    if not company_str:
        return dict(employee_meta or {})

    result = await resolve_hr_employee_funnel_for_workforce(
        db,
        tenant_id=tenant_id,
        company_id=company_str,
        explicit_funnel_id=explicit_funnel_id,
    )
    stage_code, used_fallback = resolve_recruitment_handoff_entry_stage(result.funnel)
    stage_code = _validate_pipeline_stage_for_funnel(result.funnel, stage_code)

    pipeline_meta: dict[str, Any] = {
        "funnel_id": result.funnel.id,
        "stage_code": stage_code,
        "source": result.source,
        "origin": RECRUITMENT_HANDOFF_PIPELINE_ORIGIN,
    }
    if used_fallback:
        pipeline_meta["source_handoff_fallback"] = True

    meta_out = dict(employee_meta or {})
    meta_out[EMPLOYEE_PIPELINE_META_KEY] = pipeline_meta
    return meta_out


async def merge_recruitment_handoff_pipeline_meta(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    employee_meta: Optional[dict[str, Any]] = None,
    explicit_funnel_id: Optional[str] = None,
) -> dict[str, Any]:
    """Assign pipeline on first handoff; preserve stage on repeat handoff (§5.3)."""
    meta = dict(employee_meta or {})
    existing = meta.get(EMPLOYEE_PIPELINE_META_KEY)
    if isinstance(existing, dict):
        current_stage = str(existing.get("stage_code") or "").strip()
        if current_stage:
            company_str = str(company_id or "").strip()
            if company_str:
                result = await resolve_hr_employee_funnel_for_workforce(
                    db,
                    tenant_id=tenant_id,
                    company_id=company_str,
                    explicit_funnel_id=explicit_funnel_id,
                )
                entry_stage, _ = resolve_recruitment_handoff_entry_stage(result.funnel)
                if not _pipeline_stage_update_allowed(
                    result.funnel,
                    current_stage_code=current_stage,
                    entry_stage_code=entry_stage,
                ):
                    return meta
    return await assign_hr_employee_pipeline_from_recruitment_handoff(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        employee_meta=meta,
        explicit_funnel_id=explicit_funnel_id,
    )
