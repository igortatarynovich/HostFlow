"""HR employee funnel runtime assignment (hr-employee-pipeline-p0 H4)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.funnel_types import HR_MODULE_KEY
from backend.app.models.funnel import Funnel
from backend.app.services.hr_employee_funnel_resolver import (
    HrEmployeeFunnelForbiddenError,
    HrEmployeeFunnelNotFoundError,
    HrEmployeeFunnelResolveResult,
    HrModuleNotEnabledError,
    resolve_hr_employee_funnel,
)

EMPLOYEE_PIPELINE_META_KEY = "employee_pipeline"


def _http_from_resolve_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HrModuleNotEnabledError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, HrEmployeeFunnelForbiddenError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, HrEmployeeFunnelNotFoundError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


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
