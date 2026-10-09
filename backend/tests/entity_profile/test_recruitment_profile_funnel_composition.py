"""ADR-043 Step 9A.1 — Recruitment Profile Funnel composition."""

from __future__ import annotations

import uuid

import pytest

from backend.app.entity_profile.recruitment_policy import (
    load_recruitment_profile_policy,
)
from backend.app.entity_profile.recruitment_profile_authoring import (
    RecruitmentProfileAuthoringError,
    create_recruitment_profile,
    publish_recruitment_profile_revision,
)
from backend.app.models.entity_profile import EpEntityProfile
from backend.app.models.funnel import Funnel


async def _make_funnel(
    db,
    *,
    tenant_id: str,
    module_key: str = "recruitment",
    funnel_type: str = "candidate",
) -> Funnel:
    funnel = Funnel(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=None,
        module_key=module_key,
        type=funnel_type,
        name=f"Step 9A.1 {module_key} {funnel_type}",
        is_default=False,
    )
    db.add(funnel)
    await db.flush()
    return funnel


@pytest.mark.anyio
async def test_create_snapshots_valid_tenant_recruitment_candidate_funnel(
    db,
    tenant_id: str,
) -> None:
    funnel = await _make_funnel(db, tenant_id=tenant_id)

    version = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Funnel profile",
        funnel_id=funnel.id,
    )
    head = await db.get(EpEntityProfile, version.entity_profile_id)
    policy = await load_recruitment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=version.id,
    )

    assert head is not None
    assert head.funnel_id == funnel.id
    assert version.funnel_id == funnel.id
    assert policy.funnel_id == funnel.id


@pytest.mark.anyio
async def test_revision_preserves_v1_funnel_and_reads_exact_version_snapshot(
    db,
    tenant_id: str,
) -> None:
    funnel_a = await _make_funnel(db, tenant_id=tenant_id)
    funnel_b = await _make_funnel(db, tenant_id=tenant_id)
    v1 = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Funnel profile v1",
        funnel_id=funnel_a.id,
    )

    v2 = await publish_recruitment_profile_revision(
        db,
        tenant_id=tenant_id,
        entity_profile_id=v1.entity_profile_id,
        expected_published_version=1,
        name="Funnel profile v2",
        description=None,
        default_layout_code=None,
        config={},
        funnel_id=funnel_b.id,
    )
    head = await db.get(EpEntityProfile, v1.entity_profile_id)
    policy_v1 = await load_recruitment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=v1.id,
    )
    policy_v2 = await load_recruitment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=v2.id,
    )

    assert head is not None
    assert head.funnel_id == funnel_b.id
    assert v1.funnel_id == funnel_a.id
    assert v2.funnel_id == funnel_b.id
    assert policy_v1.funnel_id == funnel_a.id
    assert policy_v2.funnel_id == funnel_b.id


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("funnel_tenant", "module_key", "funnel_type"),
    (
        ("other", "recruitment", "candidate"),
        ("same", "recruitment", "lead"),
        ("same", "hr", "candidate"),
    ),
)
async def test_create_rejects_noncanonical_funnel(
    db,
    tenant_id: str,
    funnel_tenant: str,
    module_key: str,
    funnel_type: str,
) -> None:
    selected_tenant = str(uuid.uuid4()) if funnel_tenant == "other" else tenant_id
    funnel = await _make_funnel(
        db,
        tenant_id=selected_tenant,
        module_key=module_key,
        funnel_type=funnel_type,
    )

    with pytest.raises(RecruitmentProfileAuthoringError, match="candidate Funnel"):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            name="Rejected Funnel profile",
            funnel_id=funnel.id,
        )


@pytest.mark.anyio
async def test_create_rejects_unknown_funnel(db, tenant_id: str) -> None:
    with pytest.raises(RecruitmentProfileAuthoringError, match="candidate Funnel"):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            name="Unknown Funnel profile",
            funnel_id=str(uuid.uuid4()),
        )
