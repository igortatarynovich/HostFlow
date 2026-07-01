"""Recruitment CMS default_candidate_funnel_id validation."""

from __future__ import annotations

import uuid

import pytest

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.services.recruitment_funnel_resolver import (
    RECRUITMENT_MODULE_KEY,
    RecruitmentFunnelForbiddenError,
    validate_recruitment_module_settings_for_company,
)


def _uid(prefix: str = "cms") -> str:
    return str(uuid.uuid4())


async def _seed_tenant(db, *, tenant_id: str | None = None) -> str:
    tid = tenant_id or _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"CMS Test {suffix}",
            slug=f"cms-{suffix}",
            api_key=f"cms-key-{suffix}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={"modules": {"recruitment": True, "candidates": True}},
        )
    )
    await db.flush()
    return tid


async def _seed_company(db, *, tenant_id: str, company_id: str | None = None) -> str:
    cid = company_id or _uid()
    db.add(Company(id=cid, tenant_id=tenant_id, name=f"CMS Co {cid[:8]}"))
    await db.flush()
    return cid


async def _seed_funnel(
    db,
    *,
    tenant_id: str,
    company_id: str | None,
    funnel_type: str = "candidate",
    module_key: str | None = RECRUITMENT_MODULE_KEY,
) -> Funnel:
    funnel = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key=module_key,
        type=funnel_type,
        name="CMS Pipeline",
        is_default=True,
    )
    db.add(funnel)
    await db.flush()
    return funnel


@pytest.mark.anyio
async def test_validate_recruitment_settings_accepts_company_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    funnel = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id)

    out = await validate_recruitment_module_settings_for_company(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        settings_json={"version": 1, "default_candidate_funnel_id": funnel.id},
    )
    assert out["default_candidate_funnel_id"] == funnel.id


@pytest.mark.anyio
async def test_validate_recruitment_settings_rejects_cross_company_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_a = await _seed_company(db, tenant_id=tenant_id)
    company_b = await _seed_company(db, tenant_id=tenant_id)
    funnel = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_b)

    with pytest.raises(RecruitmentFunnelForbiddenError):
        await validate_recruitment_module_settings_for_company(
            db,
            tenant_id=tenant_id,
            company_id=company_a,
            settings_json={"version": 1, "default_candidate_funnel_id": funnel.id},
        )


@pytest.mark.anyio
async def test_validate_recruitment_settings_rejects_legacy_tenant_funnel(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    legacy = await _seed_funnel(db, tenant_id=tenant_id, company_id=None, module_key=None)

    with pytest.raises(RecruitmentFunnelForbiddenError):
        await validate_recruitment_module_settings_for_company(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            settings_json={"version": 1, "default_candidate_funnel_id": legacy.id},
        )


@pytest.mark.anyio
async def test_validate_recruitment_settings_allows_clearing_default(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)

    out = await validate_recruitment_module_settings_for_company(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        settings_json={"version": 1, "default_candidate_funnel_id": None},
    )
    assert out.get("default_candidate_funnel_id") is None
