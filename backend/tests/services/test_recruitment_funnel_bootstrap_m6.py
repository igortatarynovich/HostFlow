"""M6 — company-scoped recruitment funnel bootstrap."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.recruitment_funnel_bootstrap import (
    _bootstrap_pipeline_flags,
    bootstrap_recruitment_funnels_for_company,
)
from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY


def _uid(prefix: str = "m6") -> str:
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
            name=f"M6 Test {suffix}",
            slug=f"m6-{suffix}",
            api_key=f"m6-key-{suffix}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={
                "modules": modules
                or {
                    "recruitment": True,
                    "candidates": True,
                    "leads": True,
                    "vacancies": True,
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
    company_type: str = "agency",
    enabled_modules: dict | None = None,
    company_id: str | None = None,
) -> Company:
    cid = company_id or _uid()
    extra = {"company_role": "operating", "company_type": company_type}
    company = Company(
        id=cid,
        tenant_id=tenant_id,
        name=f"M6 Co {cid[:8]}",
        extra=extra,
        enabled_modules=enabled_modules,
    )
    db.add(company)
    await db.flush()
    return company


@pytest.mark.anyio
async def test_bootstrap_creates_company_scoped_candidate_and_lead_funnels(db) -> None:
    tenant_id = await _seed_tenant(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id, company_type="agency")

    result = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="agency",
        tenant_modules={"candidates": True, "leads": True},
    )
    await db.commit()

    assert set(result.keys()) == {"candidate", "lead"}
    funnels = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company.id,
                Funnel.module_key == RECRUITMENT_MODULE_KEY,
            )
        )
    ).scalars().all()
    assert len(funnels) == 2
    assert all(f.company_id == company.id for f in funnels)
    assert all(f.module_key == RECRUITMENT_MODULE_KEY for f in funnels)

    cms = await cms_svc.get_row(db, tenant_id, company.id, RECRUITMENT_MODULE_KEY)
    assert cms is not None
    assert cms.settings_json.get("default_candidate_funnel_id") == result["candidate"]


@pytest.mark.anyio
async def test_bootstrap_skips_when_recruitment_disabled(db) -> None:
    tenant_id = await _seed_tenant(
        db,
        modules={"recruitment": False, "candidates": False, "leads": False},
    )
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(
        db,
        tenant_id=tenant_id,
        enabled_modules={"recruitment": False, "candidates": False, "leads": False},
    )

    result = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="agency",
        tenant_modules={"recruitment": False, "candidates": False, "leads": False},
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
async def test_bootstrap_services_company_gets_lead_only(db) -> None:
    tenant_id = await _seed_tenant(
        db,
        modules={"recruitment": True, "candidates": False, "leads": True},
    )
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id, company_type="services")

    result = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="services",
        tenant_modules={"candidates": False, "leads": True},
    )
    await db.commit()

    assert set(result.keys()) == {"lead"}
    types = (
        await db.execute(
            select(Funnel.type).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company.id,
            )
        )
    ).scalars().all()
    assert types == ["lead"]


@pytest.mark.anyio
async def test_bootstrap_is_idempotent(db) -> None:
    tenant_id = await _seed_tenant(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id)

    first = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="agency",
    )
    stage_count_first = (
        await db.execute(
            select(func.count())
            .select_from(FunnelStage)
            .where(FunnelStage.funnel_id == first["candidate"])
        )
    ).scalar_one()
    await db.commit()

    second = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="agency",
    )
    stage_count_second = (
        await db.execute(
            select(func.count())
            .select_from(FunnelStage)
            .where(FunnelStage.funnel_id == second["candidate"])
        )
    ).scalar_one()
    funnel_count = (
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
    await db.commit()

    assert first == second
    assert stage_count_first == stage_count_second
    assert funnel_count == 2


@pytest.mark.anyio
async def test_bootstrap_maps_candidate_stages_to_pe(db) -> None:
    tenant_id = await _seed_tenant(db)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    company = await _seed_company(db, tenant_id=tenant_id)

    result = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type="agency",
    )
    await db.commit()

    stages = (
        await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == result["candidate"]))
    ).scalars().all()
    assert stages

    mapped = [s for s in stages if s.pe_maps_to_module and s.pe_maps_to_code]
    assert len(mapped) == len(stages)


def test_bootstrap_pipeline_flags_respects_company_overrides() -> None:
    tenant = Tenant(
        id="t1",
        settings={"modules": {"recruitment": True, "candidates": True, "leads": True}},
    )
    company = Company(
        id="c1",
        tenant_id="t1",
        enabled_modules={"candidates": False, "leads": True},
    )
    create_candidate, create_lead = _bootstrap_pipeline_flags(
        tenant,
        company,
        {"candidates": True, "leads": True},
    )
    assert create_candidate is False
    assert create_lead is True
