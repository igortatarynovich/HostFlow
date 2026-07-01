from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import CandidateProfile
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant
from backend.app.models.vacancy import Vacancy
from backend.app.models.tenant import TenantLicense
from backend.app.seed_candidate_profiles import cleanup_legacy_base_candidate_profile
from backend.app.services.profile_limits import (
    check_profile_limit,
    get_tenant_profile_usage_counts,
)


pytestmark = pytest.mark.anyio


async def _create_isolated_tenant(db: AsyncSession) -> str:
    tenant_id = str(uuid.uuid4())
    db.add(
        Tenant(
            id=tenant_id,
            name=f"Profile Limits Test {tenant_id[:8]}",
            slug=f"profile-limits-{tenant_id[:8]}",
            api_key=f"profile-limits-{tenant_id[:8]}",
            is_active=True,
        )
    )
    await db.commit()
    return tenant_id


def _default_profile_config() -> dict:
    return {
        "field_configs": [
            {"field_key": "first_name", "field_type": "text", "required": True, "order": 1},
            {"field_key": "last_name", "field_type": "text", "required": True, "order": 2},
            {"field_key": "email", "field_type": "text", "required": False, "order": 3},
            {"field_key": "phone", "field_type": "text", "required": False, "order": 4},
            {"field_key": "custom_a", "field_type": "text", "required": False, "order": 5},
            {"field_key": "custom_b", "field_type": "text", "required": False, "order": 6},
        ]
    }


def _new_profile_config() -> dict:
    return {
        "field_configs": [
            {"field_key": "first_name", "field_type": "text", "required": True, "order": 1},
            {"field_key": "last_name", "field_type": "text", "required": True, "order": 2},
            {"field_key": "email", "field_type": "text", "required": False, "order": 3},
            {"field_key": "phone", "field_type": "text", "required": False, "order": 4},
        ]
    }


async def test_usage_counts_ignore_system_profiles(db: AsyncSession) -> None:
    tenant_id = await _create_isolated_tenant(db)
    db.add(
        TenantLicense(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            plan="pro",
            expires_at=date(2030, 1, 1),
            auto_renew=True,
        )
    )
    db.add(
        CandidateProfile(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            code="driver_ce_default",
            name="Driver CE default",
            config=_default_profile_config(),
            is_active=True,
            is_system=True,
        )
    )
    await db.commit()

    counts = await get_tenant_profile_usage_counts(db, tenant_id)
    assert counts == (0, 0, 0, 0)


async def test_check_profile_limit_allows_create_when_only_system_profile_exists(
    db: AsyncSession,
) -> None:
    tenant_id = await _create_isolated_tenant(db)
    db.add(
        TenantLicense(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            plan="pro",
            expires_at=date(2030, 1, 1),
            auto_renew=True,
        )
    )
    db.add(
        CandidateProfile(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            code="driver_ce_default",
            name="Driver CE default",
            config=_default_profile_config(),
            is_active=True,
            is_system=True,
        )
    )
    await db.commit()

    is_valid, limits_info, plan_name = await check_profile_limit(
        db,
        tenant_id,
        _new_profile_config(),
    )

    assert is_valid is True
    assert plan_name == "pro"
    assert limits_info["simple"]["used"] == 0
    assert limits_info["total_custom"]["used"] == 0


async def test_cleanup_legacy_base_profile_reassigns_vacancies_to_driver_default(
    db: AsyncSession,
) -> None:
    tenant_id = await _create_isolated_tenant(db)
    legacy_profile = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code="base",
        name="Legacy base",
        config={},
        is_active=True,
        is_system=True,
    )
    default_profile = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code="driver_ce_default",
        name="Driver CE default",
        config=_default_profile_config(),
        is_active=True,
        is_system=True,
    )
    company = Company(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="Test Company",
    )
    vacancy = Vacancy(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company.id,
        title="Driver CE",
        candidate_profile_id=legacy_profile.id,
    )
    db.add_all([legacy_profile, default_profile, company, vacancy])
    await db.commit()

    changed = await cleanup_legacy_base_candidate_profile(
        db,
        tenant_id,
        default_profile_id=default_profile.id,
    )

    assert changed is True

    remaining_legacy = await db.scalar(
        select(CandidateProfile.id).where(CandidateProfile.id == legacy_profile.id)
    )
    updated_vacancy = await db.get(Vacancy, vacancy.id)

    assert remaining_legacy is None
    assert updated_vacancy is not None
    assert updated_vacancy.candidate_profile_id == default_profile.id
