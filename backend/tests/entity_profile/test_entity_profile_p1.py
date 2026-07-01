"""Entity Profile Definition Registry P1 — schema, seed, resolver, read API."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.entity_profile.registry import EntityProfileRegistry, UnknownCanonicalFieldError
from backend.app.entity_profile.resolver import resolve_effective_entity_profile
from backend.app.entity_profile.seed import (
    ensure_platform_entity_profile_catalog,
    ensure_tenant_entity_profile_defaults,
)
from backend.app.field_registry.seed import ensure_platform_field_registry_catalog
from backend.app.models.entity_profile import (
    PLATFORM_TENANT_SCOPE,
    EpEntityProfile,
    EpEntityProfileField,
    EpIntakePresentation,
)


def test_p1_recruitment_manifest_declares_driver_ce_profile() -> None:
    profile = recruitment_candidate_driver_ce_profile()
    assert profile["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert profile["entity_type"] == "candidate"
    assert profile["module_owner"] == "recruitment"
    assert len(profile["fields"]) >= 5
    qualified_codes = {row["qualified_code"] for row in profile["fields"]}
    assert "recruitment.candidate.first_name" in qualified_codes
    assert "recruitment.candidate.contacts.phone" in qualified_codes
    assert profile["intake_presentations"]
    subset = profile["intake_presentations"][0]["field_subset"]
    assert set(subset).issubset(qualified_codes)


@pytest.mark.anyio
async def test_p1_platform_catalog_registers_driver_ce_profile(db) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_platform_entity_profile_catalog(db)
    await db.commit()

    profile = await EntityProfileRegistry.get_entity_profile(
        db,
        tenant_id=PLATFORM_TENANT_SCOPE,
        profile_code=DRIVER_CE_PROFILE_CODE,
    )
    assert profile is not None
    assert profile.process_profile_code == "recruitment_default"

    field_count = await db.scalar(
        select(func.count())
        .select_from(EpEntityProfileField)
        .where(EpEntityProfileField.entity_profile_id == profile.id)
    )
    assert field_count >= 5


@pytest.mark.anyio
async def test_p1_tenant_seed_idempotent(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    first = await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()
    second = await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    assert first["profiles"][DRIVER_CE_PROFILE_CODE]["field_count"] >= 5
    assert second["seeded"] is False


@pytest.mark.anyio
async def test_p1_resolver_returns_field_registry_backed_fields(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    payload = await resolve_effective_entity_profile(
        db,
        tenant_id=tenant_id,
        profile_code=DRIVER_CE_PROFILE_CODE,
        include_presentations=True,
    )
    assert payload["resolution_source"] in {"tenant_profile", "platform_catalog"}
    assert payload["profile"]["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert len(payload["fields"]) >= 5

    phone_row = next(
        row for row in payload["fields"] if row["qualified_code"] == "recruitment.candidate.contacts.phone"
    )
    assert phone_row["field"] is not None
    assert phone_row["field"]["qualified_code"] == "recruitment.candidate.contacts.phone"
    assert phone_row["field"]["field_type"] == "phone_e164"
    assert phone_row["intake_level"] == "required"

    assert payload["presentations"]
    assert "recruitment.candidate.first_name" in payload["presentations"][0]["field_subset"]


@pytest.mark.anyio
async def test_p1_rejects_ad_hoc_field_semantics(db) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_platform_field_registry_catalog(db)

    bad_profile = {
        "profile_code": f"recruitment.candidate.test_{uuid.uuid4().hex[:8]}",
        "entity_type": "candidate",
        "module_owner": "recruitment",
        "name": "Bad profile",
        "fields": [
            {
                "qualified_code": "recruitment.candidate.candidate_name",
                "sort_order": 10,
            }
        ],
    }
    with pytest.raises(UnknownCanonicalFieldError):
        await EntityProfileRegistry.register_profile(db, bad_profile, tenant_id=PLATFORM_TENANT_SCOPE)


@pytest.mark.anyio
async def test_p1_intake_subset_must_belong_to_profile(db) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_platform_field_registry_catalog(db)

    bad_profile = {
        "profile_code": f"recruitment.candidate.test_{uuid.uuid4().hex[:8]}",
        "entity_type": "candidate",
        "module_owner": "recruitment",
        "name": "Bad intake subset",
        "fields": [
            {
                "qualified_code": "recruitment.candidate.first_name",
                "sort_order": 10,
            }
        ],
        "intake_presentations": [
            {
                "presentation_code": "test.presentation",
                "field_subset": ["recruitment.candidate.last_name"],
            }
        ],
    }
    with pytest.raises(UnknownCanonicalFieldError):
        await EntityProfileRegistry.register_profile(db, bad_profile, tenant_id=PLATFORM_TENANT_SCOPE)


@pytest.mark.anyio
async def test_p1_entity_profile_read_api(client, manager_headers, tenant_id) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
        except Exception as exc:
            pytest.skip(f"Entity Profile tables not available: {exc}")
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await session.commit()

    resp = await client.get(
        f"/api/v1/platform/entity-profiles/{DRIVER_CE_PROFILE_CODE}",
        params={"include_presentations": "true"},
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert body["fields"]
    assert all(item.get("field") is not None for item in body["fields"])
    assert any(
        item["qualified_code"] == "recruitment.candidate.first_name" for item in body["fields"]
    )
    assert body["presentations"]


@pytest.mark.anyio
async def test_p1_entity_profile_read_api_not_found(client, manager_headers) -> None:
    try:
        from backend.app.db.session import async_session_maker

        async with async_session_maker() as session:
            await session.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    resp = await client.get(
        "/api/v1/platform/entity-profiles/recruitment.candidate.does_not_exist",
        headers=manager_headers,
    )
    assert resp.status_code == 404
