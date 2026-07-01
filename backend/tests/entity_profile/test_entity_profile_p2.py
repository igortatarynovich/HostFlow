"""Entity Profile Definition Registry P2 — dual-read facade + intake binding bridge."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.facade import (
    resolve_entity_profile_facade,
    resolve_entity_profile_for_intake_source,
)
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.services.intake_router import IntakeRouter


@pytest.mark.anyio
async def test_p2_facade_reads_registry_profile(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    payload = await resolve_entity_profile_facade(
        db,
        tenant_id=tenant_id,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
        include_presentations=True,
    )
    assert payload["bridge_source"] == "entity_profile_registry"
    assert payload["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert payload["resolution_source"] in {"tenant_profile", "platform_catalog"}
    assert payload["fields"]
    assert all(row.get("field") is not None for row in payload["fields"])
    assert payload["warnings"] == []


@pytest.mark.anyio
async def test_p2_facade_unknown_entity_profile_code_raises(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    with pytest.raises(EntityProfileNotFoundError):
        await resolve_entity_profile_facade(
            db,
            tenant_id=tenant_id,
            entity_profile_code="recruitment.candidate.does_not_exist",
        )


@pytest.mark.anyio
async def test_p2_facade_legacy_candidate_profile_fallback(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)

    profile = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=f"legacy_test_{uuid.uuid4().hex[:8]}",
        name="Legacy custom profile",
        config={
            "field_configs": [
                {
                    "field_key": "first_name",
                    "field_type": "text",
                    "visible": True,
                    "required": True,
                    "order": 10,
                    "label": "Given name",
                },
                {
                    "field_key": "mystery_custom_field",
                    "field_type": "text",
                    "visible": True,
                    "required": False,
                    "order": 20,
                },
            ]
        },
    )
    db.add(profile)
    await db.commit()

    payload = await resolve_entity_profile_facade(
        db,
        tenant_id=tenant_id,
        candidate_profile_id=profile.id,
    )
    assert payload["resolution_source"] == "legacy_candidate_profile"
    assert payload["bridge_source"] == "legacy_candidate_profile"
    assert payload["candidate_profile_code"] == profile.code
    assert payload["entity_profile_code"] is None
    assert "legacy_candidate_profile_fallback" in payload["warnings"]
    assert "legacy_unknown_field:mystery_custom_field" in payload["warnings"]

    first_name = next(row for row in payload["fields"] if row.get("legacy_field_key") == "first_name")
    assert first_name["qualified_code"] == "recruitment.candidate.first_name"
    assert first_name["field"] is not None
    assert first_name["label_override"] == "Given name"


@pytest.mark.anyio
async def test_p2_facade_does_not_fallback_when_entity_profile_code_missing(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    profile = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=f"legacy_only_{uuid.uuid4().hex[:8]}",
        name="Legacy only",
        config={"field_configs": []},
    )
    db.add(profile)
    await db.commit()

    with pytest.raises(EntityProfileNotFoundError):
        await resolve_entity_profile_facade(
            db,
            tenant_id=tenant_id,
            entity_profile_code="recruitment.candidate.missing_profile",
            candidate_profile_id=profile.id,
        )


@pytest.mark.anyio
async def test_p2_intake_source_entity_profile_code_binding(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT entity_profile_code FROM intake_source_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Intake entity_profile_code column not available: {exc}")

    await ensure_tenant_entity_profile_defaults(db, tenant_id)

    from backend.app.models.own_company import OwnCompany

    oc = OwnCompany(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=f"EP P2 OC {uuid.uuid4().hex[:6]}",
    )
    db.add(oc)
    await db.flush()

    form_id = f"999888777-{uuid.uuid4().hex[:8]}"
    intake_profile = await intake_crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=f"meta-driver-{uuid.uuid4().hex[:6]}",
        name="Meta driver intake",
        own_company_id=oc.id,
        provider="meta",
        channel="paid",
        route_intent=RouteIntent.candidate_application.value,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
    )
    binding = await intake_crud.create_binding(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=intake_profile.id,
        provider="meta",
        external_key=f"form_id:{form_id}",
        external_key_secondary="",
    )
    await db.commit()

    routing = await IntakeRouter.resolve(
        db,
        tenant_id=tenant_id,
        provider="meta",
        external_key=binding.external_key,
        external_key_secondary=binding.external_key_secondary,
    )
    assert routing.matched is True
    assert routing.entity_profile_code == DRIVER_CE_PROFILE_CODE

    payload = await resolve_entity_profile_for_intake_source(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=intake_profile.id,
        include_presentations=True,
    )
    assert payload["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert payload["bridge_source"] == "entity_profile_registry"
    assert payload["intake_source_profile_id"] == intake_profile.id


@pytest.mark.anyio
async def test_p2_intake_source_without_entity_profile_code_uses_legacy(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT entity_profile_code FROM intake_source_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Intake entity_profile_code column not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)

    from backend.app.models.own_company import OwnCompany

    oc = OwnCompany(id=str(uuid.uuid4()), tenant_id=tenant_id, name=f"Legacy OC {uuid.uuid4().hex[:6]}")
    db.add(oc)
    await db.flush()

    legacy = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=f"legacy_intake_{uuid.uuid4().hex[:8]}",
        name="Legacy intake profile",
        config={
            "field_configs": [
                {"field_key": "phone", "visible": True, "required": True, "order": 10},
            ]
        },
    )
    db.add(legacy)
    await db.flush()

    intake_profile = await intake_crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=f"legacy-intake-{uuid.uuid4().hex[:6]}",
        name="Legacy intake",
        own_company_id=oc.id,
        provider="meta",
        channel="paid",
        route_intent=RouteIntent.candidate_application.value,
    )
    await db.commit()

    payload = await resolve_entity_profile_for_intake_source(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=intake_profile.id,
        candidate_profile_id=legacy.id,
    )
    assert payload["resolution_source"] == "legacy_candidate_profile"
    assert payload["entity_profile_code"] is None
    phone = next(row for row in payload["fields"] if row.get("legacy_field_key") == "phone")
    assert phone["qualified_code"] == "recruitment.candidate.contacts.phone"


@pytest.mark.anyio
async def test_p2_entity_profile_resolve_api_registry(client, manager_headers, tenant_id) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
        except Exception as exc:
            pytest.skip(f"Entity Profile tables not available: {exc}")
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/entity-profiles/resolve",
        params={"entity_profile_code": DRIVER_CE_PROFILE_CODE, "include_presentations": "true"},
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert body["bridge_source"] == "entity_profile_registry"
    assert body["fields"]


@pytest.mark.anyio
async def test_p2_entity_profile_resolve_api_unknown_code_404(client, manager_headers) -> None:
    try:
        from backend.app.db.session import async_session_maker

        async with async_session_maker() as session:
            await session.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    resp = await client.get(
        "/api/v1/platform/entity-profiles/resolve",
        params={"entity_profile_code": "recruitment.candidate.not_real"},
        headers=manager_headers,
    )
    assert resp.status_code == 404
