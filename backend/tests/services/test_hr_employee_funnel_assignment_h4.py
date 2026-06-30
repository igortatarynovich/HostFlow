"""H4 — HR employee funnel runtime assignment + meta stages contracts."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.constants.funnel_types import HR_EMPLOYEE_FUNNEL_TYPE, HR_MODULE_KEY
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.process_engine.constants import HR_MODULE
from backend.app.process_engine.pipeline_mapping import apply_pe_mapping_to_funnel_stage
from backend.app.process_engine.seed import ensure_platform_process_engine_catalog
from backend.app.services.hr_employee_funnel_assignment import (
    EMPLOYEE_PIPELINE_META_KEY,
    assign_hr_employee_pipeline_on_create,
    first_hr_employee_funnel_stage_code,
)
from backend.app.services.hr_employee_funnel_bootstrap import (
    HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES,
    bootstrap_hr_employee_funnel_for_company,
)
from backend.app.services.workforce_employees import create_employee


def _uid(prefix: str = "h4") -> str:
    return str(uuid.uuid4())


async def _seed_tenant(
    db,
    *,
    modules: dict | None = None,
    tenant_id: str | None = None,
) -> Tenant:
    tid = tenant_id or _uid()
    suffix = tid.replace("-", "")[:10]
    tenant = Tenant(
        id=tid,
        name=f"H4 Test {suffix}",
        slug=f"h4-{suffix}",
        api_key=f"h4-key-{suffix}",
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
    db.add(tenant)
    await db.flush()
    return tenant


async def _seed_company(db, *, tenant_id: str) -> Company:
    company = Company(
        id=_uid(),
        tenant_id=tenant_id,
        name="H4 Operating Co",
        extra={"company_role": "operating", "company_type": "employer"},
    )
    db.add(company)
    await db.flush()
    return company


async def _seed_hr_funnel_with_stages(
    db,
    *,
    tenant_id: str,
    company_id: str,
) -> Funnel:
    await ensure_platform_process_engine_catalog(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one()
    await bootstrap_hr_employee_funnel_for_company(db, tenant=tenant, company=company)
    funnel = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company_id,
                Funnel.module_key == HR_MODULE_KEY,
                Funnel.type == HR_EMPLOYEE_FUNNEL_TYPE,
            )
        )
    ).scalar_one()
    return funnel


def test_workforce_create_wires_hr_assignment_not_recruitment_resolver() -> None:
    source = Path("backend/app/services/workforce_employees.py").read_text(encoding="utf-8")
    assert "assign_hr_employee_pipeline_on_create" in source
    assert "resolve_recruitment_funnel" not in source


def test_meta_stages_supports_employee_pipeline_type() -> None:
    source = Path("backend/app/api/v1/meta.py").read_text(encoding="utf-8")
    assert "pipeline_type == \"employee\"" in source
    assert "resolve_hr_employee_funnel" in source
    assert "^(candidate|lead|employee)$" in source


def test_first_hr_employee_funnel_stage_code_prefers_hr_pe_mapping() -> None:
    funnel = Funnel(id="f1", tenant_id="t1", type=HR_EMPLOYEE_FUNNEL_TYPE, name="Test")
    funnel.stages = [
        FunnelStage(
            funnel_id="f1",
            code="ignored",
            label="Ignored",
            order=0,
            pe_maps_to_module="recruitment",
            pe_maps_to_code="new",
        ),
        FunnelStage(
            funnel_id="f1",
            code="handoff_pending",
            label="Handoff Pending",
            order=1,
            pe_maps_to_module=HR_MODULE_KEY,
            pe_maps_to_code="handoff_pending",
        ),
    ]
    assert first_hr_employee_funnel_stage_code(funnel) == "handoff_pending"


@pytest.mark.anyio
async def test_assign_hr_employee_pipeline_on_create_sets_first_stage(db) -> None:
    tenant = await _seed_tenant(db)
    company = await _seed_company(db, tenant_id=tenant.id)
    await _seed_hr_funnel_with_stages(db, tenant_id=tenant.id, company_id=company.id)
    await db.commit()

    meta = await assign_hr_employee_pipeline_on_create(
        db,
        tenant_id=tenant.id,
        company_id=company.id,
        employee_meta={},
    )
    pipeline = meta[EMPLOYEE_PIPELINE_META_KEY]
    assert pipeline["stage_code"] == HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES[0]
    assert pipeline["funnel_id"]
    assert pipeline["source"] in {"cms", "company_default", "platform_seed"}


@pytest.mark.anyio
async def test_assign_hr_employee_pipeline_respects_explicit_stage(db) -> None:
    tenant = await _seed_tenant(db)
    company = await _seed_company(db, tenant_id=tenant.id)
    await _seed_hr_funnel_with_stages(db, tenant_id=tenant.id, company_id=company.id)
    await db.commit()

    meta = await assign_hr_employee_pipeline_on_create(
        db,
        tenant_id=tenant.id,
        company_id=company.id,
        employee_meta={},
        pipeline_stage="verification",
    )
    assert meta[EMPLOYEE_PIPELINE_META_KEY]["stage_code"] == "verification"


@pytest.mark.anyio
async def test_assign_hr_employee_pipeline_rejects_invalid_stage(db) -> None:
    tenant = await _seed_tenant(db)
    company = await _seed_company(db, tenant_id=tenant.id)
    await _seed_hr_funnel_with_stages(db, tenant_id=tenant.id, company_id=company.id)
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await assign_hr_employee_pipeline_on_create(
            db,
            tenant_id=tenant.id,
            company_id=company.id,
            employee_meta={},
            pipeline_stage="ready_for_handoff",
        )
    assert exc.value.status_code == 422


@pytest.mark.anyio
async def test_assign_hr_employee_pipeline_requires_hr_module(db) -> None:
    tenant = await _seed_tenant(
        db,
        modules={"hr": False, "recruitment": False, "candidates": False, "leads": False},
    )
    company = await _seed_company(db, tenant_id=tenant.id)
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await assign_hr_employee_pipeline_on_create(
            db,
            tenant_id=tenant.id,
            company_id=company.id,
            employee_meta={},
        )
    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_create_employee_without_company_skips_pipeline_binding(db) -> None:
    tenant = await _seed_tenant(db)
    await db.commit()

    row = await create_employee(
        db,
        tenant.id,
        display_name="No company scope",
    )
    await db.commit()

    assert row.meta is None or EMPLOYEE_PIPELINE_META_KEY not in (row.meta or {})


@pytest.mark.anyio
async def test_create_employee_binds_hr_pipeline_when_company_present(db) -> None:
    tenant = await _seed_tenant(db)
    company = await _seed_company(db, tenant_id=tenant.id)
    await _seed_hr_funnel_with_stages(db, tenant_id=tenant.id, company_id=company.id)
    await db.commit()

    row = await create_employee(
        db,
        tenant.id,
        display_name="HR Pipeline Employee",
        company_id=company.id,
    )
    await db.commit()

    pipeline = (row.meta or {}).get(EMPLOYEE_PIPELINE_META_KEY) or {}
    assert pipeline.get("funnel_id")
    assert pipeline.get("stage_code") == HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES[0]

    stored = (
        await db.execute(
            select(WorkforceEmployee).where(WorkforceEmployee.id == row.id)
        )
    ).scalar_one()
    assert stored.meta[EMPLOYEE_PIPELINE_META_KEY]["stage_code"] == HR_EMPLOYEE_BOOTSTRAP_STAGE_CODES[0]


@pytest.mark.anyio
async def test_create_employee_default_stage_when_pipeline_stage_omitted(db) -> None:
    tenant = await _seed_tenant(db)
    company = await _seed_company(db, tenant_id=tenant.id)
    funnel = await _seed_hr_funnel_with_stages(db, tenant_id=tenant.id, company_id=company.id)
    stages = (
        await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == funnel.id))
    ).scalars().all()
    for stage in stages:
        if not stage.pe_maps_to_module:
            await apply_pe_mapping_to_funnel_stage(
                db,
                stage,
                tenant_id=tenant.id,
                module=HR_MODULE,
                code=str(stage.code),
            )
    await db.commit()

    row = await create_employee(
        db,
        tenant.id,
        display_name="Default stage employee",
        company_id=company.id,
    )
    await db.commit()

    assert (
        row.meta[EMPLOYEE_PIPELINE_META_KEY]["stage_code"]
        == first_hr_employee_funnel_stage_code(funnel)
    )
