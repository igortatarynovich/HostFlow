"""Resolve HR-owned employee funnels per company (hr-employee-pipeline-p0 H2).

Resolution chain (no recruitment fallback):
1. explicit funnel_id
2. company_module_settings.hr.employee_pipeline_funnel_id
3. company default funnel (company_id + module_key=hr + type=employee)
4. platform seed funnel (tenant_id='default') — strangler only
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.constants.funnel_types import (
    HR_EMPLOYEE_FUNNEL_TYPE,
    HR_MODULE_KEY,
    PLATFORM_SEED_TENANT_ID,
)
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.company_module_access import company_allows_module

logger = logging.getLogger(__name__)

HrEmployeeFunnelSource = Literal["explicit", "cms", "company_default", "platform_seed"]


class HrEmployeeFunnelResolveError(Exception):
    """Base error for HR employee funnel resolution failures."""


class HrModuleNotEnabledError(HrEmployeeFunnelResolveError):
    """HR module is not enabled for the company on this tenant."""


class HrEmployeeFunnelNotFoundError(HrEmployeeFunnelResolveError):
    """No HR employee funnel could be resolved for the requested scope."""


class HrEmployeeFunnelForbiddenError(HrEmployeeFunnelResolveError):
    """Explicit funnel_id violates company/module/type ownership — no fallback."""


@dataclass(frozen=True)
class HrEmployeeFunnelResolveResult:
    funnel: Funnel
    source: HrEmployeeFunnelSource
    used_platform_seed_strangler: bool


async def resolve_hr_employee_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    explicit_funnel_id: Optional[str] = None,
    tenant: Optional[Tenant] = None,
    company: Optional[Company] = None,
) -> HrEmployeeFunnelResolveResult:
    """Resolve the HR employee pipeline funnel for ``company_id``."""
    tid = str(tenant_id).strip()
    cid = str(company_id).strip()
    if not tid or not cid:
        raise HrEmployeeFunnelNotFoundError("tenant_id and company_id are required")

    tenant_obj = tenant
    if tenant_obj is None:
        tenant_obj = await db.get(Tenant, tid)
    if tenant_obj is None:
        raise HrEmployeeFunnelNotFoundError(f"tenant not found: {tid}")

    company_obj = company
    if company_obj is None:
        company_obj = await cms_svc.get_company_for_tenant(db, tid, cid)
    if company_obj is None:
        raise HrEmployeeFunnelNotFoundError(f"company not found: {cid}")

    if not company_allows_module(tenant_obj, company_obj, HR_MODULE_KEY):
        raise HrModuleNotEnabledError(f"hr module is not enabled for company {cid}")

    if explicit_funnel_id:
        explicit = await _resolve_explicit_hr_employee_funnel(
            db,
            funnel_id=str(explicit_funnel_id).strip(),
            tenant_id=tid,
            company_id=cid,
        )
        return HrEmployeeFunnelResolveResult(
            funnel=explicit,
            source="explicit",
            used_platform_seed_strangler=explicit.tenant_id == PLATFORM_SEED_TENANT_ID,
        )

    cms_funnel = await _resolve_cms_employee_pipeline_funnel(db, tenant_id=tid, company_id=cid)
    if cms_funnel is not None:
        return HrEmployeeFunnelResolveResult(
            funnel=cms_funnel,
            source="cms",
            used_platform_seed_strangler=False,
        )

    company_default = await _load_default_hr_employee_funnel(
        db,
        tenant_id=tid,
        company_id=cid,
    )
    if company_default is not None:
        return HrEmployeeFunnelResolveResult(
            funnel=company_default,
            source="company_default",
            used_platform_seed_strangler=False,
        )

    platform = await _load_platform_seed_hr_employee_funnel(db)
    if platform is not None:
        logger.info(
            "hr_employee_funnel_resolver platform seed fallback tenant=%s company=%s funnel=%s",
            tid,
            cid,
            platform.id,
        )
        return HrEmployeeFunnelResolveResult(
            funnel=platform,
            source="platform_seed",
            used_platform_seed_strangler=True,
        )

    raise HrEmployeeFunnelNotFoundError(
        f"no hr employee funnel for tenant={tid} company={cid}"
    )


async def validate_hr_employee_funnel_id_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    funnel_id: str,
) -> Funnel:
    """Validate explicit HR employee funnel binding. Raises on violation."""
    return await _resolve_explicit_hr_employee_funnel(
        db,
        funnel_id=funnel_id,
        tenant_id=tenant_id,
        company_id=company_id,
    )


async def validate_hr_module_settings_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    settings_json: dict[str, Any],
) -> dict[str, Any]:
    """Validate HR CMS JSON; enforce company-owned employee pipeline funnel pointer."""
    from backend.app.schemas.company_module_settings_json import HrModuleSettingsV1

    normalized = HrModuleSettingsV1.model_validate(settings_json).model_dump(mode="json")
    raw_fid = normalized.get("employee_pipeline_funnel_id")
    if not raw_fid or not str(raw_fid).strip():
        return normalized

    funnel = await validate_hr_employee_funnel_id_for_company(
        db,
        tenant_id=str(tenant_id),
        company_id=str(company_id),
        funnel_id=str(raw_fid).strip(),
    )
    if not funnel.company_id or str(funnel.company_id) != str(company_id).strip():
        raise HrEmployeeFunnelForbiddenError(
            "employee_pipeline_funnel_id must be a company-scoped HR employee funnel"
        )
    if str(funnel.module_key or "") != HR_MODULE_KEY:
        raise HrEmployeeFunnelForbiddenError(
            "employee_pipeline_funnel_id must use module_key=hr"
        )
    if str(funnel.type or "") != HR_EMPLOYEE_FUNNEL_TYPE:
        raise HrEmployeeFunnelForbiddenError(
            "employee_pipeline_funnel_id must use type=employee"
        )
    return normalized


async def _resolve_explicit_hr_employee_funnel(
    db: AsyncSession,
    *,
    funnel_id: str,
    tenant_id: str,
    company_id: str,
) -> Funnel:
    if not funnel_id:
        raise HrEmployeeFunnelNotFoundError("explicit funnel_id is empty")

    funnel = await _load_hr_employee_funnel_by_id(
        db,
        funnel_id=funnel_id,
        tenant_id=tenant_id,
    )
    if funnel is None:
        raise HrEmployeeFunnelNotFoundError(f"explicit funnel not found: {funnel_id}")

    f_company = str(funnel.company_id or "").strip() or None
    if f_company and f_company != str(company_id).strip():
        raise HrEmployeeFunnelForbiddenError(
            f"funnel {funnel_id} belongs to company {f_company}, not {company_id}"
        )

    f_module = str(funnel.module_key or "").strip() or None
    if f_module and f_module != HR_MODULE_KEY:
        raise HrEmployeeFunnelForbiddenError(
            f"funnel {funnel_id} module_key={f_module} is not hr"
        )

    if str(funnel.type or "") != HR_EMPLOYEE_FUNNEL_TYPE:
        raise HrEmployeeFunnelForbiddenError(
            f"funnel {funnel_id} type={funnel.type} is not employee"
        )

    return funnel


async def _resolve_cms_employee_pipeline_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> Optional[Funnel]:
    row = await cms_svc.get_row(db, tenant_id, company_id, HR_MODULE_KEY)
    if row is None:
        return None
    settings = row.settings_json if isinstance(row.settings_json, dict) else {}
    raw_fid = settings.get("employee_pipeline_funnel_id")
    if not raw_fid or not str(raw_fid).strip():
        return None
    try:
        return await validate_hr_employee_funnel_id_for_company(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            funnel_id=str(raw_fid).strip(),
        )
    except HrEmployeeFunnelForbiddenError:
        logger.warning(
            "hr_employee_funnel_resolver cms funnel forbidden tenant=%s company=%s funnel=%s",
            tenant_id,
            company_id,
            raw_fid,
        )
        return None
    except HrEmployeeFunnelNotFoundError:
        return None


async def _load_hr_employee_funnel_by_id(
    db: AsyncSession,
    *,
    funnel_id: str,
    tenant_id: str,
) -> Optional[Funnel]:
    stmt = (
        select(Funnel)
        .options(selectinload(Funnel.stages))
        .where(
            Funnel.id == funnel_id,
            Funnel.tenant_id.in_([tenant_id, PLATFORM_SEED_TENANT_ID]),
            Funnel.module_key == HR_MODULE_KEY,
            Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _load_default_hr_employee_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> Optional[Funnel]:
    stmt = (
        select(Funnel)
        .options(selectinload(Funnel.stages))
        .where(
            Funnel.tenant_id == tenant_id,
            Funnel.company_id == company_id,
            Funnel.module_key == HR_MODULE_KEY,
            Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            Funnel.is_default.is_(True),
        )
        .order_by(Funnel.name.asc(), Funnel.id.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _load_platform_seed_hr_employee_funnel(db: AsyncSession) -> Optional[Funnel]:
    stmt = (
        select(Funnel)
        .options(selectinload(Funnel.stages))
        .where(
            Funnel.tenant_id == PLATFORM_SEED_TENANT_ID,
            Funnel.company_id.is_(None),
            Funnel.module_key == HR_MODULE_KEY,
            Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            Funnel.is_default.is_(True),
        )
        .order_by(Funnel.name.asc(), Funnel.id.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()
