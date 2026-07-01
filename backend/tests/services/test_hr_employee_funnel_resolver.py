"""Tests for hr_employee_funnel_resolver (H2)."""

from __future__ import annotations

import uuid

import pytest

from backend.app.constants.funnel_types import HR_EMPLOYEE_FUNNEL_TYPE, HR_MODULE_KEY, PLATFORM_SEED_TENANT_ID
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.hr_employee_funnel_resolver import (
    HrEmployeeFunnelForbiddenError,
    HrEmployeeFunnelNotFoundError,
    HrModuleNotEnabledError,
    resolve_hr_employee_funnel,
)


def _uid(prefix: str = "hrf") -> str:
    return str(uuid.uuid4())


async def _seed_tenant(
    db,
    *,
    modules: dict | None = None,
    tenant_id: str | None = None,
) -> str:
    tid = tenant_id or _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"HR Funnel Test {suffix}",
            slug=f"hrf-{suffix}",
            api_key=f"hrf-key-{suffix}",
            type=TenantType.company,
            status=TenantStatus.active,
            settings={
                "modules": modules
                or {
                    "hr": True,
                    "recruitment": False,
                    "candidates": False,
                    "leads": False,
                }
            },
        )
    )
    await db.flush()
    return tid


async def _seed_company(db, *, tenant_id: str, company_id: str | None = None) -> str:
    cid = company_id or _uid()
    db.add(Company(id=cid, tenant_id=tenant_id, name=f"HR Co {cid[:8]}"))
    await db.flush()
    return cid


async def _seed_hr_employee_funnel(
    db,
    *,
    tenant_id: str,
    company_id: str | None = None,
    is_default: bool = True,
    name: str = "HR Employee Pipeline",
) -> Funnel:
    funnel = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key=HR_MODULE_KEY,
        type=HR_EMPLOYEE_FUNNEL_TYPE,
        name=name,
        is_default=is_default,
    )
    db.add(funnel)
    await db.flush()
    return funnel


@pytest.mark.anyio
async def test_resolve_prefers_cms_employee_pipeline_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    default_funnel = await _seed_hr_employee_funnel(
        db, tenant_id=tenant_id, company_id=company_id, name="Company Default"
    )
    cms_funnel = await _seed_hr_employee_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        is_default=False,
        name="CMS Selected",
    )
    await cms_svc.upsert_settings(
        db,
        tenant_id,
        company_id,
        HR_MODULE_KEY,
        settings_json={"version": 1, "employee_pipeline_funnel_id": cms_funnel.id},
        is_enabled=True,
    )
    await db.commit()

    result = await resolve_hr_employee_funnel(db, tenant_id=tenant_id, company_id=company_id)
    assert result.funnel.id == cms_funnel.id
    assert result.source == "cms"
    assert result.used_platform_seed_strangler is False
    assert result.funnel.id != default_funnel.id


@pytest.mark.anyio
async def test_resolve_company_default_without_cms(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    default_funnel = await _seed_hr_employee_funnel(
        db, tenant_id=tenant_id, company_id=company_id, name="Company Default"
    )
    await db.commit()

    result = await resolve_hr_employee_funnel(db, tenant_id=tenant_id, company_id=company_id)
    assert result.funnel.id == default_funnel.id
    assert result.source == "company_default"


@pytest.mark.anyio
async def test_resolve_platform_seed_strangler(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    platform_funnel = await _seed_hr_employee_funnel(
        db,
        tenant_id=PLATFORM_SEED_TENANT_ID,
        company_id=None,
        name="Platform HR Employee",
    )
    await db.commit()

    result = await resolve_hr_employee_funnel(db, tenant_id=tenant_id, company_id=company_id)
    assert result.funnel.id == platform_funnel.id
    assert result.source == "platform_seed"
    assert result.used_platform_seed_strangler is True


@pytest.mark.anyio
async def test_resolve_explicit_funnel_id(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    explicit = await _seed_hr_employee_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        is_default=False,
        name="Explicit",
    )
    await db.commit()

    result = await resolve_hr_employee_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        explicit_funnel_id=explicit.id,
    )
    assert result.funnel.id == explicit.id
    assert result.source == "explicit"


@pytest.mark.anyio
async def test_explicit_funnel_wrong_company_forbidden(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_a = await _seed_company(db, tenant_id=tenant_id)
    company_b = await _seed_company(db, tenant_id=tenant_id)
    funnel = await _seed_hr_employee_funnel(db, tenant_id=tenant_id, company_id=company_b)
    await db.commit()

    with pytest.raises(HrEmployeeFunnelForbiddenError):
        await resolve_hr_employee_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_a,
            explicit_funnel_id=funnel.id,
        )


@pytest.mark.anyio
async def test_explicit_recruitment_funnel_forbidden(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    wrong = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key="recruitment",
        type="candidate",
        name="Recruitment Funnel",
        is_default=True,
    )
    db.add(wrong)
    await db.commit()

    with pytest.raises(HrEmployeeFunnelForbiddenError):
        await resolve_hr_employee_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            explicit_funnel_id=wrong.id,
        )


@pytest.mark.anyio
async def test_resolve_raises_when_hr_disabled(db) -> None:
    tenant_id = await _seed_tenant(
        db,
        modules={"hr": False, "recruitment": False, "candidates": False, "leads": False},
    )
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await db.commit()

    with pytest.raises(HrModuleNotEnabledError):
        await resolve_hr_employee_funnel(db, tenant_id=tenant_id, company_id=company_id)


@pytest.mark.anyio
async def test_resolve_raises_when_no_funnel_exists(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await db.commit()

    with pytest.raises(HrEmployeeFunnelNotFoundError):
        await resolve_hr_employee_funnel(db, tenant_id=tenant_id, company_id=company_id)
