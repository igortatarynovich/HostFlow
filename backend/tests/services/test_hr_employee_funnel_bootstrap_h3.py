"""H3 — company-scoped HR employee funnel bootstrap."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.constants.funnel_types import HR_EMPLOYEE_FUNNEL_TYPE, HR_MODULE_KEY
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.process_engine.seed import ensure_platform_process_engine_catalog
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.hr_employee_funnel_bootstrap import (
    HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES,
    bootstrap_hr_employee_funnel_for_company,
    hr_employee_bootstrap_stages,
)
from backend.app.services.recruitment_funnel_bootstrap import (
    bootstrap_recruitment_funnels_for_company,
)
from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY


def _uid(prefix: str = "h3") -> str:
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
            name=f"H3 Test {suffix}",
            slug=f"h3-{suffix}",
            api_key=f"h3-key-{suffix}",
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


async def _seed_company(
    db,
    *,
    tenant_id: str,
    enabled_modules: dict | None = None,
    company_id: str | None = None,
) -> Company:
    cid = company_id or _uid()
    company = Company(
        id=cid,
        tenant_id=tenant_id,
        name=f"H3 Co {cid[:8]}",
        extra={"company_role": "operating", "company_type": "employer"},
        enabled_modules=enabled_modules,
    )
    db.add(company)
    await db.flush()
    return company


def test_hr_employee_bootstrap_stages_come_from_manifest_only() -> None:
    rows = hr_employee_bootstrap_stages()
    assert [code for code, *_ in rows] == list(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)
    assert all(label for _, label, _, _ in rows)
    assert rows[-1][3] is True  # active is terminal


@pytest.mark.anyio
async def test_bootstrap_creates_company_scoped_hr_employee_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id)

    result = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    await db.commit()

    assert result == {HR_EMPLOYEE_FUNNEL_TYPE: result[HR_EMPLOYEE_FUNNEL_TYPE]}
    funnel = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company.id,
                Funnel.module_key == HR_MODULE_KEY,
                Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            )
        )
    ).scalar_one()
    assert funnel.is_default is True
    assert funnel.company_id == company.id

    cms = await cms_svc.get_row(db, tenant_id, company.id, HR_MODULE_KEY)
    assert cms is not None
    assert cms.settings_json.get("employee_pipeline_funnel_id") == funnel.id


@pytest.mark.anyio
async def test_bootstrap_skips_when_hr_disabled(db) -> None:
    tenant_id = await _seed_tenant(
        db,
        modules={"hr": False, "recruitment": False, "candidates": False, "leads": False},
    )
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(
        db,
        tenant_id=tenant_id,
        enabled_modules={"hr": False},
    )

    result = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    await db.commit()

    assert result == {}
    count = (
        await db.execute(
            select(func.count())
            .select_from(Funnel)
            .where(Funnel.tenant_id == tenant_id, Funnel.company_id == company.id)
        )
    ).scalar_one()
    assert count == 0


@pytest.mark.anyio
async def test_bootstrap_is_idempotent(db) -> None:
    tenant_id = await _seed_tenant(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id)

    first = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    stage_count_first = (
        await db.execute(
            select(func.count())
            .select_from(FunnelStage)
            .where(FunnelStage.funnel_id == first[HR_EMPLOYEE_FUNNEL_TYPE])
        )
    ).scalar_one()
    await db.commit()

    second = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    stage_count_second = (
        await db.execute(
            select(func.count())
            .select_from(FunnelStage)
            .where(FunnelStage.funnel_id == second[HR_EMPLOYEE_FUNNEL_TYPE])
        )
    ).scalar_one()
    funnel_count = (
        await db.execute(
            select(func.count())
            .select_from(Funnel)
            .where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company.id,
                Funnel.module_key == HR_MODULE_KEY,
                Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            )
        )
    ).scalar_one()
    await db.commit()

    assert first == second
    assert stage_count_first == stage_count_second
    assert stage_count_first == len(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)
    assert funnel_count == 1


@pytest.mark.anyio
async def test_bootstrap_does_not_overwrite_existing_cms_funnel_id(db) -> None:
    tenant_id = await _seed_tenant(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id)
    existing_funnel_id = _uid("existing")

    await cms_svc.upsert_settings(
        db,
        tenant_id,
        company.id,
        HR_MODULE_KEY,
        settings_json={
            "version": 1,
            "employee_pipeline_funnel_id": existing_funnel_id,
        },
        is_enabled=True,
    )
    await db.commit()

    result = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    await db.commit()

    cms = await cms_svc.get_row(db, tenant_id, company.id, HR_MODULE_KEY)
    assert cms is not None
    assert cms.settings_json.get("employee_pipeline_funnel_id") == existing_funnel_id
    assert result[HR_EMPLOYEE_FUNNEL_TYPE] != existing_funnel_id


@pytest.mark.anyio
async def test_hr_only_tenant_does_not_create_recruitment_funnels(db) -> None:
    tenant_id = await _seed_tenant(
        db,
        modules={"hr": True, "recruitment": False, "candidates": False, "leads": False},
    )
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id)

    recruitment_result = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="employer",
        tenant_modules={"recruitment": False, "candidates": False, "leads": False},
    )
    hr_result = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    await db.commit()

    assert recruitment_result == {}
    assert HR_EMPLOYEE_FUNNEL_TYPE in hr_result

    recruitment_count = (
        await db.execute(
            select(func.count())
            .select_from(Funnel)
            .where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company.id,
                Funnel.module_key == RECRUITMENT_MODULE_KEY,
            )
        )
    ).scalar_one()
    hr_count = (
        await db.execute(
            select(func.count())
            .select_from(Funnel)
            .where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company.id,
                Funnel.module_key == HR_MODULE_KEY,
                Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            )
        )
    ).scalar_one()
    assert recruitment_count == 0
    assert hr_count == 1


@pytest.mark.anyio
async def test_bootstrap_maps_stages_to_hr_pe(db) -> None:
    await ensure_platform_process_engine_catalog(db)
    tenant_id = await _seed_tenant(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id)

    result = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    await db.commit()

    stages = (
        await db.execute(
            select(FunnelStage).where(
                FunnelStage.funnel_id == result[HR_EMPLOYEE_FUNNEL_TYPE]
            )
        )
    ).scalars().all()
    assert len(stages) == len(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)

    mapped = [s for s in stages if s.pe_maps_to_module == HR_MODULE_KEY and s.pe_maps_to_code]
    assert len(mapped) == len(stages)
    assert {s.pe_maps_to_code for s in mapped} == set(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)
