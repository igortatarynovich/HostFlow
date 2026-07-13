"""Tests for launch-search role defaults (funnels + candidate profiles)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.services.launch_search_role_defaults import (
    GENERAL_CANDIDATE_DEFAULT_CODE,
    OFFICE_WORKER_DEFAULT_CODE,
    WAREHOUSE_FUNNEL_NAME,
    WAREHOUSE_WORKER_DEFAULT_CODE,
    ensure_launch_search_role_defaults,
    ensure_launch_search_role_funnels_for_company,
)


@pytest.mark.anyio
async def test_ensure_launch_search_role_defaults_creates_profiles_and_funnels(
    db,
    tenant_id: str,
):
    company = (
        await db.execute(select(Company).where(Company.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    assert company is not None
    extra = dict(company.extra or {})
    extra["company_role"] = "operating"
    company.extra = extra
    await db.flush()

    company_id = str(company.id)
    await ensure_launch_search_role_funnels_for_company(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    await db.commit()

    result = await ensure_launch_search_role_defaults(db, tenant_id)
    await db.commit()
    assert result["company_id"] == company_id
    assert "warehouse" in result["funnel_ids"]
    assert "office" in result["profile_ids"]

    profiles = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.code.in_(
                    [
                        WAREHOUSE_WORKER_DEFAULT_CODE,
                        OFFICE_WORKER_DEFAULT_CODE,
                        GENERAL_CANDIDATE_DEFAULT_CODE,
                    ]
                ),
            )
        )
    ).scalars().all()
    assert len(profiles) == 3

    funnels = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company_id,
                Funnel.name == WAREHOUSE_FUNNEL_NAME,
            )
        )
    ).scalars().all()
    assert len(funnels) == 1
