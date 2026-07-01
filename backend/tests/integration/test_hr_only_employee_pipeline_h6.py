"""H6 — HR-only tenant acceptance: employee pipeline without Recruitment."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.api.v1.meta import stages_meta
from backend.app.constants.funnel_types import HR_EMPLOYEE_FUNNEL_TYPE, HR_MODULE_KEY
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.process_engine.seed import ensure_platform_process_engine_catalog
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.hr_employee_funnel_assignment import EMPLOYEE_PIPELINE_META_KEY
from backend.app.services.hr_employee_funnel_bootstrap import (
    HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES,
    bootstrap_hr_employee_funnel_for_company,
)
from backend.app.services.hr_employee_funnel_resolver import resolve_hr_employee_funnel
from backend.app.services.recruitment_funnel_bootstrap import (
    bootstrap_recruitment_funnels_for_company,
)
from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY
from backend.app.services.workforce_employees import create_employee

RECRUITMENT_STAGE_CODES = frozenset(
    {
        "new",
        "contacted",
        "docs_wait",
        "ready_for_handoff",
        "hired",
        "rejected",
    }
)


def _uid(prefix: str = "h6") -> str:
    return str(uuid.uuid4())


HR_ONLY_MODULES = {
    "hr": True,
    "recruitment": False,
    "candidates": False,
    "leads": False,
    "vacancies": False,
}


async def _seed_hr_only_tenant(db) -> Tenant:
    tid = _uid()
    suffix = tid.replace("-", "")[:10]
    tenant = Tenant(
        id=tid,
        name=f"HR-only {suffix}",
        slug=f"hronly-{suffix}",
        api_key=f"hronly-key-{suffix}",
        type=TenantType.company,
        status=TenantStatus.active,
        settings={"modules": dict(HR_ONLY_MODULES)},
    )
    db.add(tenant)
    await db.flush()
    return tenant


async def _seed_operating_company(db, *, tenant_id: str) -> Company:
    company = Company(
        id=_uid(),
        tenant_id=tenant_id,
        name="HR-only Operating Co",
        extra={"company_role": "operating", "company_type": "employer"},
    )
    db.add(company)
    await db.flush()
    return company


@pytest.mark.anyio
async def test_hr_only_tenant_employee_pipeline_acceptance(db) -> None:
    """§9 independence test — bootstrap, resolve, meta stages, employee create; zero recruitment funnels."""
    await ensure_platform_process_engine_catalog(db)
    tenant = await _seed_hr_only_tenant(db)
    company = await _seed_operating_company(db, tenant_id=tenant.id)

    recruitment_bootstrap = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="employer",
        tenant_modules=dict(HR_ONLY_MODULES),
    )
    assert recruitment_bootstrap == {}

    hr_bootstrap = await bootstrap_hr_employee_funnel_for_company(
        db,
        tenant=tenant,
        company=company,
    )
    await db.commit()

    assert set(hr_bootstrap.keys()) == {HR_EMPLOYEE_FUNNEL_TYPE}

    hr_funnel_count = (
        await db.execute(
            select(func.count())
            .select_from(Funnel)
            .where(
                Funnel.tenant_id == tenant.id,
                Funnel.company_id == company.id,
                Funnel.module_key == HR_MODULE_KEY,
                Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            )
        )
    ).scalar_one()
    recruitment_funnel_count = (
        await db.execute(
            select(func.count())
            .select_from(Funnel)
            .where(
                Funnel.tenant_id == tenant.id,
                Funnel.company_id == company.id,
                Funnel.module_key == RECRUITMENT_MODULE_KEY,
            )
        )
    ).scalar_one()
    assert hr_funnel_count == 1
    assert recruitment_funnel_count == 0

    resolved = await resolve_hr_employee_funnel(
        db,
        tenant_id=tenant.id,
        company_id=company.id,
    )
    assert resolved.funnel.module_key == HR_MODULE_KEY
    assert resolved.funnel.type == HR_EMPLOYEE_FUNNEL_TYPE
    assert resolved.funnel.company_id == company.id
    assert resolved.funnel.id == hr_bootstrap[HR_EMPLOYEE_FUNNEL_TYPE]

    stages = (
        await db.execute(
            select(FunnelStage).where(FunnelStage.funnel_id == resolved.funnel.id)
        )
    ).scalars().all()
    assert len(stages) == len(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)
    assert all(s.pe_maps_to_module == HR_MODULE_KEY and s.pe_maps_to_code for s in stages)
    assert {s.pe_maps_to_code for s in stages} == set(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)

    cms = await cms_svc.get_row(db, tenant.id, company.id, HR_MODULE_KEY)
    assert cms is not None
    assert cms.settings_json.get("employee_pipeline_funnel_id") == resolved.funnel.id

    meta = await stages_meta(
        db=db,
        tenant_id_header=tenant.id,
        company_id=company.id,
        pipeline_type="employee",
        current_user=None,
    )
    assert meta.get("pipeline_type") == "employee"
    assert meta.get("funnel_id") == resolved.funnel.id
    order = list(meta.get("order") or [])
    assert order
    assert set(order) == set(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)
    assert not (set(order) & RECRUITMENT_STAGE_CODES)
    custom = list(meta.get("custom_stages") or [])
    assert len(custom) == len(HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES)
    assert all(row.get("pe_maps_to_module") == HR_MODULE_KEY for row in custom)
    assert all(row.get("pe_maps_to_code") for row in custom)

    employee = await create_employee(
        db,
        tenant.id,
        display_name="HR-only hire",
        company_id=company.id,
    )
    await db.commit()

    pipeline = (employee.meta or {}).get(EMPLOYEE_PIPELINE_META_KEY) or {}
    assert pipeline.get("funnel_id") == resolved.funnel.id
    assert pipeline.get("stage_code") == HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES[0]
    assert pipeline.get("source") in {"cms", "company_default"}
