"""Tests for launch-search vacancy setup (auto funnel bootstrap)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.models.vacancy import Vacancy
from backend.app.services.launch_search_vacancy_setup import (
    LaunchSearchSetupError,
    ensure_launch_search_vacancy_defaults,
    ensure_recruitment_funnels_for_company,
)


def _uid(prefix: str = "ls") -> str:
    return str(uuid.uuid4())


async def _seed_tenant(db, *, tenant_id: str | None = None) -> str:
    tid = tenant_id or _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"Launch Search {suffix}",
            slug=f"ls-{suffix}",
            api_key=f"ls-key-{suffix}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={
                "modules": {
                    "recruitment": True,
                    "candidates": True,
                    "leads": True,
                    "vacancies": True,
                },
                "business_type": "agency",
            },
        )
    )
    await db.flush()
    return tid


async def _seed_company(db, *, tenant_id: str, company_role: str = "operating") -> Company:
    company = Company(
        id=_uid("co"),
        tenant_id=tenant_id,
        name="Test Company",
        extra={"company_role": company_role, "company_type": "agency"},
    )
    db.add(company)
    await db.flush()
    return company


@pytest.mark.anyio
async def test_ensure_recruitment_funnels_for_company_creates_lead_and_candidate(db):
    tenant_id = await _seed_tenant(db)
    company = await _seed_company(db, tenant_id=tenant_id)
    await db.commit()

    result = await ensure_recruitment_funnels_for_company(
        db,
        tenant_id=tenant_id,
        company_id=str(company.id),
    )
    await db.commit()

    assert result.get("candidate")
    assert result.get("lead")

    funnels = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == str(company.id),
            )
        )
    ).scalars().all()
    types = {f.type for f in funnels}
    assert "candidate" in types
    assert "lead" in types


@pytest.mark.anyio
async def test_ensure_launch_search_vacancy_defaults_attaches_funnel(db):
    tenant_id = await _seed_tenant(db)
    company = await _seed_company(db, tenant_id=tenant_id)
    vacancy = Vacancy(
        id=_uid("vac"),
        tenant_id=tenant_id,
        company_id=str(company.id),
        title="Driver search",
        employment_type="full_time",
    )
    db.add(vacancy)
    await db.commit()

    result = await ensure_launch_search_vacancy_defaults(
        db,
        tenant_id=tenant_id,
        vacancy_id=str(vacancy.id),
        role="driver",
    )
    await db.commit()

    assert result["funnel_id"]
    assert result["lead_funnel_id"]

    refreshed = (
        await db.execute(select(Vacancy).where(Vacancy.id == str(vacancy.id)))
    ).scalar_one()
    assert refreshed.funnel_id == result["funnel_id"]


@pytest.mark.anyio
async def test_ensure_launch_search_vacancy_defaults_missing_vacancy_raises(db):
    tenant_id = await _seed_tenant(db)
    await db.commit()

    with pytest.raises(LaunchSearchSetupError, match="vacancy not found"):
        await ensure_launch_search_vacancy_defaults(
            db,
            tenant_id=tenant_id,
            vacancy_id=_uid("missing"),
            role="driver",
        )
