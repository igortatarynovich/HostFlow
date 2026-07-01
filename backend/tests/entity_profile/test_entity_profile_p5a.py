"""Entity Profile P5A — Form Presentation Runtime (foundation-only)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.entity_profile.constants import (
    DRIVER_CE_INTAKE_PRESENTATION_CODE,
    DRIVER_CE_PROFILE_CODE,
)
from backend.app.entity_profile.presentation_runtime import (
    FORM_PRESENTATION_RUNTIME_V1,
    FormPresentationNotFoundError,
    resolve_form_presentation,
    resolve_form_presentation_for_intake_source,
)
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing import crud as intake_crud


@pytest.mark.anyio
async def test_p5a_resolve_driver_ce_meta_short(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_intake_presentations LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile presentations not available: {exc}")

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    payload = await resolve_form_presentation(
        db,
        tenant_id=tenant_id,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
        presentation_code=DRIVER_CE_INTAKE_PRESENTATION_CODE,
    )
    assert payload["contract_version"] == FORM_PRESENTATION_RUNTIME_V1
    assert payload["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert payload["presentation_code"] == DRIVER_CE_INTAKE_PRESENTATION_CODE
    assert payload["ownership"] == "display_only"
    assert payload["warnings"] == []

    qualified = [row["qualified_code"] for row in payload["fields"]]
    assert qualified == [
        "recruitment.candidate.first_name",
        "recruitment.candidate.last_name",
        "recruitment.candidate.contacts.phone",
    ]

    labels = {row["qualified_code"]: row["label"] for row in payload["fields"]}
    assert labels["recruitment.candidate.first_name"] == "Imię"
    assert labels["recruitment.candidate.last_name"] == "Nazwisko"
    assert labels["recruitment.candidate.contacts.phone"] == "Telefon"

    for row in payload["fields"]:
        assert row.get("field") is not None
        assert row["field"].get("qualified_code") == row["qualified_code"]
        assert row.get("field_type")


@pytest.mark.anyio
async def test_p5a_presentation_rejects_unknown_field_in_subset(db, tenant_id: str) -> None:
    from backend.app.entity_profile.registry import EntityProfileRegistry
    from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
    from backend.app.models.entity_profile import EpEntityProfile, EpIntakePresentation

    try:
        await db.execute(text("SELECT 1 FROM ep_intake_presentations LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile presentations not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    code = f"test.profile.{uuid.uuid4().hex[:8]}"
    await EntityProfileRegistry.register_profile(
        db,
        {
            "profile_code": code,
            "entity_type": "candidate",
            "module_owner": "recruitment",
            "name": "Test profile",
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.first_name",
                    "sort_order": 10,
                    "intake_level": "required",
                },
            ],
        },
        tenant_id=tenant_id,
    )
    profile = (
        await db.execute(
            text("SELECT id FROM ep_entity_profiles WHERE tenant_id = :t AND profile_code = :c LIMIT 1"),
            {"t": tenant_id, "c": code},
        )
    ).scalar_one()

    # Simulate manually corrupted presentation row (runtime guard, not register-time).
    db.add(
        EpIntakePresentation(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            entity_profile_id=str(profile),
            presentation_code=f"{code}.short",
            field_subset=[
                "recruitment.candidate.first_name",
                "crm.client.company_name",
            ],
            presentation_overrides={},
        )
    )
    await db.commit()

    payload = await resolve_form_presentation(
        db,
        tenant_id=tenant_id,
        entity_profile_code=code,
        presentation_code=f"{code}.short",
    )
    assert len(payload["fields"]) == 1
    assert payload["fields"][0]["qualified_code"] == "recruitment.candidate.first_name"
    assert any("presentation_field_not_in_profile:" in w for w in payload["warnings"])


@pytest.mark.anyio
async def test_p5a_unknown_presentation_raises(db, tenant_id: str) -> None:
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    with pytest.raises(FormPresentationNotFoundError):
        await resolve_form_presentation(
            db,
            tenant_id=tenant_id,
            entity_profile_code=DRIVER_CE_PROFILE_CODE,
            presentation_code="recruitment.candidate.driver_ce.does_not_exist",
        )


@pytest.mark.anyio
async def test_p5a_resolve_via_intake_source(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT entity_profile_code FROM intake_source_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Intake entity_profile_code not available: {exc}")

    from backend.app.models.own_company import OwnCompany

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    oc = OwnCompany(id=str(uuid.uuid4()), tenant_id=tenant_id, name=f"P5A OC {uuid.uuid4().hex[:6]}")
    db.add(oc)
    await db.flush()

    intake_profile = await intake_crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=f"p5a-intake-{uuid.uuid4().hex[:6]}",
        name="P5A intake",
        own_company_id=oc.id,
        provider="meta",
        channel="paid",
        route_intent=RouteIntent.candidate_application.value,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
    )
    await db.commit()

    payload = await resolve_form_presentation_for_intake_source(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=intake_profile.id,
        presentation_code=DRIVER_CE_INTAKE_PRESENTATION_CODE,
    )
    assert payload["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert len(payload["fields"]) == 3


@pytest.mark.anyio
async def test_p5a_api_get_presentation(client, manager_headers, tenant_id: str) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1 FROM ep_intake_presentations LIMIT 1"))
        except Exception as exc:
            pytest.skip(f"Entity Profile presentations not available: {exc}")
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await session.commit()

    resp = await client.get(
        f"/api/v1/platform/entity-profiles/{DRIVER_CE_PROFILE_CODE}/presentations/{DRIVER_CE_INTAKE_PRESENTATION_CODE}",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["contract_version"] == FORM_PRESENTATION_RUNTIME_V1
    assert body["ownership"] == "display_only"
    assert len(body["fields"]) == 3


@pytest.mark.anyio
async def test_p5a_api_presentation_not_found_404(client, manager_headers, tenant_id: str) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await session.commit()

    resp = await client.get(
        f"/api/v1/platform/entity-profiles/{DRIVER_CE_PROFILE_CODE}/presentations/not.real",
        headers=manager_headers,
    )
    assert resp.status_code == 404
