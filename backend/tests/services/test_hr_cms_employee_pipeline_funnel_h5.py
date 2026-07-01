"""H5 — HR CMS employee_pipeline_funnel_id validation."""

from __future__ import annotations

import uuid

import pytest

from backend.app.constants.funnel_types import HR_EMPLOYEE_FUNNEL_TYPE, HR_MODULE_KEY
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.services.hr_employee_funnel_resolver import (
    HrEmployeeFunnelForbiddenError,
    validate_hr_module_settings_for_company,
)
from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY


def _uid(prefix: str = "h5cms") -> str:
    return str(uuid.uuid4())


async def _seed_tenant(db, *, tenant_id: str | None = None) -> str:
    tid = tenant_id or _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"H5 CMS {suffix}",
            slug=f"h5cms-{suffix}",
            api_key=f"h5cms-key-{suffix}",
            type=TenantType.company,
            status=TenantStatus.active,
            settings={"modules": {"hr": True, "recruitment": False}},
        )
    )
    await db.flush()
    return tid


async def _seed_company(db, *, tenant_id: str, company_id: str | None = None) -> str:
    cid = company_id or _uid()
    db.add(Company(id=cid, tenant_id=tenant_id, name=f"H5 Co {cid[:8]}"))
    await db.flush()
    return cid


async def _seed_funnel(
    db,
    *,
    tenant_id: str,
    company_id: str | None,
    funnel_type: str = HR_EMPLOYEE_FUNNEL_TYPE,
    module_key: str | None = HR_MODULE_KEY,
) -> Funnel:
    funnel = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key=module_key,
        type=funnel_type,
        name="CMS HR Pipeline",
        is_default=True,
    )
    db.add(funnel)
    await db.flush()
    return funnel


@pytest.mark.anyio
async def test_validate_hr_settings_accepts_company_employee_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    funnel = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id)

    out = await validate_hr_module_settings_for_company(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        settings_json={"version": 1, "employee_pipeline_funnel_id": funnel.id},
    )
    assert out["employee_pipeline_funnel_id"] == funnel.id


@pytest.mark.anyio
async def test_validate_hr_settings_rejects_cross_company_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_a = await _seed_company(db, tenant_id=tenant_id)
    company_b = await _seed_company(db, tenant_id=tenant_id)
    funnel = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_b)

    with pytest.raises(HrEmployeeFunnelForbiddenError):
        await validate_hr_module_settings_for_company(
            db,
            tenant_id=tenant_id,
            company_id=company_a,
            settings_json={"version": 1, "employee_pipeline_funnel_id": funnel.id},
        )


@pytest.mark.anyio
async def test_validate_hr_settings_rejects_legacy_tenant_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    legacy = await _seed_funnel(db, tenant_id=tenant_id, company_id=None, module_key=None)

    with pytest.raises(HrEmployeeFunnelForbiddenError):
        await validate_hr_module_settings_for_company(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            settings_json={"version": 1, "employee_pipeline_funnel_id": legacy.id},
        )


@pytest.mark.anyio
async def test_validate_hr_settings_rejects_recruitment_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    wrong = await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        funnel_type="candidate",
        module_key=RECRUITMENT_MODULE_KEY,
    )

    with pytest.raises(HrEmployeeFunnelForbiddenError):
        await validate_hr_module_settings_for_company(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            settings_json={"version": 1, "employee_pipeline_funnel_id": wrong.id},
        )


@pytest.mark.anyio
async def test_validate_hr_settings_allows_clearing_pipeline_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)

    out = await validate_hr_module_settings_for_company(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        settings_json={"version": 1, "employee_pipeline_funnel_id": None},
    )
    assert out.get("employee_pipeline_funnel_id") is None
