"""Tests for tenant intake bootstrap on registration/onboarding."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.entity_profile.constants import OFFICE_WORKER_PROFILE_CODE
from backend.app.models.entity_profile import EpEntityProfile
from backend.app.services.tenant_intake_bootstrap import ensure_tenant_intake_bootstrap_defaults


@pytest.mark.anyio
async def test_ensure_tenant_intake_bootstrap_defaults_seeds_entity_profiles(
    db,
    tenant_id: str,
):
    await db.execute(
        EpEntityProfile.__table__.delete().where(EpEntityProfile.tenant_id == tenant_id)
    )
    await db.commit()

    result = await ensure_tenant_intake_bootstrap_defaults(db, tenant_id=tenant_id)
    await db.commit()

    assert "entity_profiles" in result
    codes = (
        await db.execute(
            select(EpEntityProfile.profile_code).where(EpEntityProfile.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert OFFICE_WORKER_PROFILE_CODE in codes
