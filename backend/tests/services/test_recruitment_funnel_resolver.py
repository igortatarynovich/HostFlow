"""Tests for recruitment_funnel_resolver (module-owned pipelines P0)."""

from __future__ import annotations

import uuid

import pytest

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.recruitment_funnel_resolver import (
    PLATFORM_SEED_TENANT_ID,
    RecruitmentFunnelForbiddenError,
    RecruitmentFunnelNotFoundError,
    RecruitmentModuleNotEnabledError,
    resolve_recruitment_funnel,
)


def _uid(prefix: str = "mop") -> str:
    return str(uuid.uuid4())


async def _seed_tenant(db, *, tenant_id: str | None = None) -> str:
    tid = tenant_id or _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"MOP Test {suffix}",
            slug=f"mop-{suffix}",
            api_key=f"mop-key-{suffix}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={"modules": {"recruitment": True, "candidates": True, "leads": True, "vacancies": True}},
        )
    )
    await db.flush()
    return tid


async def _seed_company(db, *, tenant_id: str, company_id: str | None = None) -> str:
    cid = company_id or _uid()
    db.add(Company(id=cid, tenant_id=tenant_id, name=f"MOP Co {cid[:8]}"))
    await db.flush()
    return cid


async def _seed_funnel(
    db,
    *,
    tenant_id: str,
    funnel_type: str = "candidate",
    company_id: str | None = None,
    is_default: bool = True,
    name: str = "Test Pipeline",
    module_key: str = "recruitment",
) -> Funnel:
    funnel = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key=module_key,
        type=funnel_type,
        name=name,
        is_default=is_default,
    )
    db.add(funnel)
    await db.flush()
    return funnel


@pytest.mark.anyio
async def test_resolve_prefers_cms_default_candidate_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    default_funnel = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id, name="Company Default")
    cms_funnel = await _seed_funnel(
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
        "recruitment",
        settings_json={"version": 1, "default_candidate_funnel_id": cms_funnel.id},
        is_enabled=True,
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
    )
    assert result.funnel.id == cms_funnel.id
    assert result.source == "cms"
    assert result.used_legacy_strangler is False
    assert result.funnel.id != default_funnel.id


@pytest.mark.anyio
async def test_resolve_company_default_without_cms(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    default_funnel = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id, name="Company Default")
    await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        is_default=False,
        name="Secondary",
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
    )
    assert result.funnel.id == default_funnel.id
    assert result.source == "company_default"
    assert result.used_legacy_strangler is False


@pytest.mark.anyio
async def test_resolve_legacy_tenant_fallback(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    legacy = await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=None,
        name="Legacy Tenant Default",
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
    )
    assert result.funnel.id == legacy.id
    assert result.source == "legacy_tenant"
    assert result.used_legacy_strangler is True


@pytest.mark.anyio
async def test_resolve_platform_seed_last_resort(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    platform = await _seed_funnel(
        db,
        tenant_id=PLATFORM_SEED_TENANT_ID,
        company_id=None,
        name="Platform Seed",
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
    )
    assert result.funnel.id == platform.id
    assert result.source == "platform_seed"
    assert result.used_legacy_strangler is True


@pytest.mark.anyio
async def test_resolve_explicit_funnel_id(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id, name="Default")
    explicit = await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        is_default=False,
        name="Explicit",
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
        explicit_funnel_id=explicit.id,
    )
    assert result.funnel.id == explicit.id
    assert result.source == "explicit"


@pytest.mark.anyio
async def test_explicit_candidate_funnel_allows_tenant_catalog(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_a = await _seed_company(db, tenant_id=tenant_id)
    company_b = await _seed_company(db, tenant_id=tenant_id)
    funnel_b = await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_b,
        name="Company B funnel",
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_a,
        pipeline_type="candidate",
        explicit_funnel_id=funnel_b.id,
    )
    assert result.funnel.id == funnel_b.id
    assert result.source == "explicit"


@pytest.mark.anyio
async def test_explicit_candidate_legacy_tenant_funnel_allowed(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    legacy = await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=None,
        name="Legacy Tenant Default",
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
        explicit_funnel_id=legacy.id,
    )
    assert result.funnel.id == legacy.id
    assert result.source == "explicit"


@pytest.mark.anyio
async def test_explicit_lead_funnel_wrong_company_forbidden(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_a = await _seed_company(db, tenant_id=tenant_id)
    company_b = await _seed_company(db, tenant_id=tenant_id)
    funnel_b = await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_b,
        funnel_type="lead",
        name="Company B lead funnel",
    )
    await db.commit()

    with pytest.raises(RecruitmentFunnelForbiddenError):
        await resolve_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_a,
            pipeline_type="lead",
            explicit_funnel_id=funnel_b.id,
        )


@pytest.mark.anyio
async def test_explicit_missing_funnel_not_fallback(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id)
    await db.commit()

    with pytest.raises(RecruitmentFunnelNotFoundError):
        await resolve_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            pipeline_type="candidate",
            explicit_funnel_id=str(uuid.uuid4()),
        )


@pytest.mark.anyio
async def test_resolve_raises_when_recruitment_disabled(db) -> None:
    tenant_id = await _seed_tenant(db)
    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    tenant.settings = {
        "modules": {
            "recruitment": False,
            "candidates": False,
            "leads": False,
            "vacancies": False,
        }
    }
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id)
    await db.commit()

    with pytest.raises(RecruitmentModuleNotEnabledError):
        await resolve_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            pipeline_type="candidate",
        )


@pytest.mark.anyio
async def test_resolve_raises_when_no_funnel_exists(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await db.commit()

    with pytest.raises(RecruitmentFunnelNotFoundError):
        await resolve_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            pipeline_type="candidate",
        )


@pytest.mark.anyio
async def test_resolve_lead_pipeline_type(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    lead_funnel = await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        funnel_type="lead",
        name="Lead Default",
    )
    await db.commit()

    result = await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="lead",
    )
    assert result.funnel.id == lead_funnel.id
    assert result.source == "company_default"
