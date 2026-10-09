"""ADR-043 Step 9A.2 — Recruitment Profile Process Profile composition."""

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
from backend.app.models.process_engine import PeProcessProfile


async def _make_process_profile(
    db,
    *,
    tenant_id: str,
    code: str | None = None,
    module: str = "recruitment",
    status: str = "active",
) -> PeProcessProfile:
    profile = PeProcessProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        module=module,
        code=code or f"process_{uuid.uuid4().hex[:8]}",
        registry_version="process_engine_v1",
        status=status,
        name="Step 9A.2 Process Profile",
        config={},
        is_system=False,
        is_default=False,
    )
    db.add(profile)
    await db.flush()
    return profile


@pytest.mark.anyio
async def test_create_snapshots_tenant_process_profile_identity_and_code(
    db,
    tenant_id: str,
) -> None:
    process_profile = await _make_process_profile(
        db,
        tenant_id=tenant_id,
        code="tenant_recruitment_process",
    )

    version = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Process-composed profile",
        process_profile_id=process_profile.id,
    )
    head = await db.get(EpEntityProfile, version.entity_profile_id)
    policy = await load_recruitment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=version.id,
    )

    assert head is not None
    assert head.process_profile_id == process_profile.id
    assert head.process_profile_code == process_profile.code
    assert version.process_profile_id == process_profile.id
    assert version.process_profile_code == process_profile.code
    assert policy.process_profile_id == process_profile.id


@pytest.mark.anyio
async def test_revision_preserves_v1_process_identity_and_reads_exact_version(
    db,
    tenant_id: str,
) -> None:
    process_a = await _make_process_profile(db, tenant_id=tenant_id, code="process_a")
    process_b = await _make_process_profile(db, tenant_id=tenant_id, code="process_b")
    v1 = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Process profile v1",
        process_profile_id=process_a.id,
    )

    head = await db.get(EpEntityProfile, v1.entity_profile_id)
    assert head is not None
    head.process_profile_code = "stale_conflicting_code"
    await db.flush()

    v2 = await publish_recruitment_profile_revision(
        db,
        tenant_id=tenant_id,
        entity_profile_id=v1.entity_profile_id,
        expected_published_version=1,
        name="Process profile v2",
        description=None,
        default_layout_code=None,
        config={},
        process_profile_id=process_b.id,
    )
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

    assert v1.process_profile_id == process_a.id
    assert v1.process_profile_code == process_a.code
    assert v2.process_profile_id == process_b.id
    assert v2.process_profile_code == process_b.code
    assert policy_v1.process_profile_id == process_a.id
    assert policy_v2.process_profile_id == process_b.id
    assert head.process_profile_id == process_b.id
    assert head.process_profile_code == process_b.code


@pytest.mark.anyio
async def test_unknown_process_profile_is_rejected(db, tenant_id: str) -> None:
    with pytest.raises(RecruitmentProfileAuthoringError, match="tenant-owned"):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            name="Unknown process profile",
            process_profile_id=str(uuid.uuid4()),
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("scope", "module", "status"),
    (
        ("other", "recruitment", "active"),
        ("platform", "recruitment", "active"),
        ("same", "hr", "active"),
        ("same", "recruitment", "archived"),
    ),
)
async def test_noncanonical_process_profile_is_rejected(
    db,
    tenant_id: str,
    scope: str,
    module: str,
    status: str,
) -> None:
    selected_tenant = {
        "same": tenant_id,
        "other": str(uuid.uuid4()),
        "platform": "",
    }[scope]
    process_profile = await _make_process_profile(
        db,
        tenant_id=selected_tenant,
        module=module,
        status=status,
    )

    with pytest.raises(RecruitmentProfileAuthoringError, match="tenant-owned"):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            name="Rejected process profile",
            process_profile_id=process_profile.id,
        )
