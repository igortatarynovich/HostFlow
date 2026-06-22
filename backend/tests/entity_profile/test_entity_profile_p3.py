"""Entity Profile Definition Registry P3 — ingest runtime bridge."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select, text

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.ingest_runtime import (
    prepare_meta_ingest_runtime,
    prepare_public_intake_runtime,
)
from backend.app.entity_profile.mapping_validation import (
    validate_mapping_rules_for_profile,
)
from backend.app.entity_profile.reverse_map import find_entity_profile_code_by_legacy_candidate_code
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models import Lead
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing import crud as intake_crud
from backend.tests.modules.leads.conftest import post_meta_lead


def _meta_payload(*, form_id: str, phone: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": str(uuid.uuid4().int)[:15],
                            "form_id": form_id,
                            "field_data": [
                                {"name": "phone_number", "values": [phone]},
                                {"name": "first_name", "values": ["Jan"]},
                            ],
                        }
                    }
                ]
            }
        ]
    }


@pytest.mark.anyio
async def test_p3_mapping_rejects_target_outside_entity_profile(db, tenant_id: str) -> None:
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    allowed = {
        "recruitment.candidate.first_name",
        "recruitment.candidate.contacts.phone",
    }
    rules = [
        {"source": "first_name", "target": "first_name", "qualified_field_code": "recruitment.candidate.first_name"},
        {"source": "phone_number", "target": "phone", "qualified_field_code": "recruitment.candidate.contacts.phone"},
        {"source": "company", "target": "company_name_hint", "qualified_field_code": "crm.client.company_name"},
    ]
    result = validate_mapping_rules_for_profile(
        rules,
        allowed_qualified_codes=allowed,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
        resolution_source="tenant_profile",
    )
    assert len(result.accepted_rules) == 2
    assert len(result.rejected_rules) == 1
    assert any("mapping_target_rejected:" in w for w in result.warnings)


@pytest.mark.anyio
async def test_p3_reverse_map_driver_ce_default(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    mapped = await find_entity_profile_code_by_legacy_candidate_code(
        db,
        tenant_id=tenant_id,
        legacy_candidate_profile_code="driver_ce_default",
    )
    assert mapped == DRIVER_CE_PROFILE_CODE


@pytest.mark.anyio
async def test_p3_prepare_meta_ingest_runtime_scopes_mapping(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    from backend.app.models.own_company import OwnCompany

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    oc = OwnCompany(id=str(uuid.uuid4()), tenant_id=tenant_id, name=f"P3 OC {uuid.uuid4().hex[:6]}")
    db.add(oc)
    await db.flush()

    form_id = f"form-{uuid.uuid4().hex[:8]}"
    intake_profile = await intake_crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=f"meta-p3-{uuid.uuid4().hex[:6]}",
        name="Meta P3",
        own_company_id=oc.id,
        provider="meta",
        channel="paid",
        route_intent=RouteIntent.candidate_application.value,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
    )
    await intake_crud.create_binding(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=intake_profile.id,
        provider="meta",
        external_key=f"form_id:{form_id}",
        external_key_secondary="",
    )
    await db.execute(
        text(
            """
            INSERT INTO meta_lead_settings (tenant_id, auto_create_enabled, mask_pii_in_logs, field_mapping)
            VALUES (:t, true, true, CAST(:m AS jsonb))
            ON CONFLICT (tenant_id) DO UPDATE SET field_mapping = CAST(:m AS jsonb)
            """
        ),
        {
            "t": tenant_id,
            "m": json.dumps(
                [
                    {"source": "phone_number", "target": "phone", "format": "phone", "qualified_field_code": "recruitment.candidate.contacts.phone"},
                    {"source": "first_name", "target": "first_name", "qualified_field_code": "recruitment.candidate.first_name"},
                    {"source": "company", "target": "company_name_hint", "qualified_field_code": "crm.client.company_name"},
                ]
            ),
        },
    )
    await db.commit()

    payload = _meta_payload(form_id=form_id, phone="+48111222333")
    validated, envelope, route, profile_view = await prepare_meta_ingest_runtime(
        db,
        tenant_id=tenant_id,
        source="meta",
        raw_payload=payload,
    )
    assert envelope.entity_profile_code == DRIVER_CE_PROFILE_CODE
    assert route.entity_profile_code == DRIVER_CE_PROFILE_CODE
    assert len(validated) == 2
    assert envelope.mapping_result["rejected_count"] == 1
    assert profile_view["bridge_source"] == "entity_profile_registry"


@pytest.mark.anyio
async def test_p3_meta_ingest_stamps_envelope_on_lead(client, manager_headers, tenant_id: str) -> None:
    try:
        from backend.app.db.session import async_session_maker

        async with async_session_maker() as session:
            await session.execute(text("SELECT entity_profile_code FROM intake_source_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"P2 intake binding not available: {exc}")

    from backend.app.models.own_company import OwnCompany

    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        oc = OwnCompany(id=str(uuid.uuid4()), tenant_id=tenant_id, name=f"P3 ingest {uuid.uuid4().hex[:6]}")
        session.add(oc)
        await session.flush()
        form_id = f"form-{uuid.uuid4().hex[:8]}"
        intake_profile = await intake_crud.create_profile(
            session,
            tenant_id=tenant_id,
            code=f"meta-env-{uuid.uuid4().hex[:6]}",
            name="Meta envelope",
            own_company_id=oc.id,
            provider="meta",
            channel="paid",
            route_intent=RouteIntent.candidate_application.value,
            entity_profile_code=DRIVER_CE_PROFILE_CODE,
        )
        await intake_crud.create_binding(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=intake_profile.id,
            provider="meta",
            external_key=f"form_id:{form_id}",
            external_key_secondary="",
        )
        await session.commit()

    phone = f"+48{uuid.uuid4().int % 10**9:09d}"
    resp = await post_meta_lead(client, manager_headers, _meta_payload(form_id=form_id, phone=phone))
    assert resp.status_code in (200, 201), resp.text
    lead_id = resp.json().get("lead_id")
    assert lead_id

    async with async_session_maker() as session:
        lead = (
            await session.execute(select(Lead).where(Lead.id == lead_id))
        ).scalar_one_or_none()
        assert lead is not None
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        envelope = norm.get("ingest_envelope_v1") or {}
        assert envelope.get("entity_profile_code") == DRIVER_CE_PROFILE_CODE
        assert envelope.get("route_intent")
        assert "mapping_result" in envelope


@pytest.mark.anyio
async def test_p3_legacy_reverse_map_via_facade(db, tenant_id: str) -> None:
    from backend.app.entity_profile.facade import resolve_entity_profile_facade
    from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
    from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile

    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await ensure_driver_ce_default_profile(db, tenant_id)
    await db.commit()

    payload = await resolve_entity_profile_facade(
        db,
        tenant_id=tenant_id,
        candidate_profile_code="driver_ce_default",
    )
    assert payload["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert payload["bridge_source"] == "entity_profile_registry"
    assert "legacy_reverse_map_applied" in payload.get("warnings", [])


@pytest.mark.anyio
async def test_p3_legacy_without_reverse_map_warns(db, tenant_id: str) -> None:
    from backend.app.entity_profile.facade import resolve_entity_profile_facade
    from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
    from backend.app.models.candidate_profile import CandidateProfile

    await ensure_tenant_field_registry_defaults(db, tenant_id)

    legacy = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=f"orphan_profile_{uuid.uuid4().hex[:8]}",
        name="Orphan",
        config={"field_configs": [{"field_key": "phone", "visible": True}]},
    )
    db.add(legacy)
    await db.commit()

    payload = await resolve_entity_profile_facade(
        db,
        tenant_id=tenant_id,
        candidate_profile_code=legacy.code,
    )
    assert payload["resolution_source"] == "legacy_candidate_profile"
    assert payload.get("entity_profile_code") is None
    assert "legacy_reverse_map_missing" in payload.get("warnings", [])


@pytest.mark.anyio
async def test_p3_public_intake_runtime_builds_envelope(db, tenant_id: str) -> None:
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    intake_state = {
        "contacts": {"phone": "+48123456789", "email": "driver@example.com"},
        "personal": {"citizenship": "PL"},
        "lead_form": {"id": str(uuid.uuid4()), "public_slug": "driver-ce"},
    }
    envelope, profile_view, validation = await prepare_public_intake_runtime(
        db,
        tenant_id=tenant_id,
        intake_state=intake_state,
        entity_profile_code=DRIVER_CE_PROFILE_CODE,
    )
    assert envelope.entity_profile_code == DRIVER_CE_PROFILE_CODE
    assert envelope.normalized_payload.get("contacts.phone") == "+48123456789"
    assert validation.accepted_rules
    assert profile_view["bridge_source"] == "entity_profile_registry"
