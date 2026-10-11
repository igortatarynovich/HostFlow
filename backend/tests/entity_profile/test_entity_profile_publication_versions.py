"""ADR-043 Slice 1 — immutable Entity Profile publication identity."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.publication_versions import (
    get_publication_version,
    list_publication_versions,
    publish_entity_profile,
)
from backend.app.models.entity_profile import EpEntityProfile, EpEntityProfileVersion


async def _make_profile(db, *, tenant_id: str) -> EpEntityProfile:
    profile = EpEntityProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        profile_code=f"recruitment.candidate.publish_{uuid.uuid4().hex[:8]}",
        registry_version="entity_profile_v1",
        status="active",
        name="Recruitment profile v1",
        description="Initial profile",
        is_system=False,
        entity_type="candidate",
        module_owner="recruitment",
        default_layout_code="candidate.default",
        document_pack_code="legacy.driver.pack",
        process_profile_code="recruitment_default",
        version=1,
        config={"source": "test", "revision": 1},
    )
    db.add(profile)
    await db.flush()
    return profile


@pytest.mark.anyio
async def test_publish_creates_first_immutable_profile_revision(db, tenant_id: str) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)

    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
    )

    assert published.version == 1
    assert published.entity_profile_id == profile.id
    assert published.tenant_id == tenant_id
    assert published.name == "Recruitment profile v1"
    assert published.module_owner == "recruitment"
    assert published.config == {"source": "test", "revision": 1}

    assert profile.published_version == 1
    assert profile.published_at == published.published_at

    # ADR-043: legacy Document Pack authority is not frozen into the target
    # immutable profile policy identity.
    assert not hasattr(published, "document_pack_code")


@pytest.mark.anyio
async def test_second_publish_appends_without_mutating_first_revision(db, tenant_id: str) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)

    first = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
    )
    first_id = first.id

    profile.name = "Recruitment profile v2"
    profile.description = "Changed after first publication"
    profile.config = {"source": "test", "revision": 2}
    await db.flush()

    second = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
    )

    assert second.version == 2
    assert second.id != first_id
    assert profile.published_version == 2

    historical = await get_publication_version(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        version=1,
    )
    assert historical is not None
    assert historical.id == first_id
    assert historical.name == "Recruitment profile v1"
    assert historical.description == "Initial profile"
    assert historical.config == {"source": "test", "revision": 1}

    versions = await list_publication_versions(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
    )
    assert [row.version for row in versions] == [1, 2]
    assert versions[1].name == "Recruitment profile v2"


@pytest.mark.anyio
async def test_publication_identity_is_persistent_and_queryable(db, tenant_id: str) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)

    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
    )
    await db.flush()

    loaded = await db.scalar(
        select(EpEntityProfileVersion).where(
            EpEntityProfileVersion.id == published.id
        )
    )

    assert loaded is not None
    assert loaded.id == published.id
    assert loaded.entity_profile_id == profile.id
    assert loaded.version == 1


@pytest.mark.anyio
async def test_publish_rejects_missing_or_wrong_tenant_profile(db, tenant_id: str) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)

    with pytest.raises(EntityProfileNotFoundError):
        await publish_entity_profile(
            db,
            tenant_id=f"wrong-{tenant_id}",
            entity_profile_id=profile.id,
        )

    with pytest.raises(EntityProfileNotFoundError):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=str(uuid.uuid4()),
        )
