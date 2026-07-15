"""C3 — Entity Profile seeds for role/country variants + intake mapping/smoke."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import (
    DRIVER_CE_UA_PROFILE_CODE,
    WAREHOUSE_WORKER_PROFILE_CODE,
)
from backend.app.entity_profile.facade import resolve_entity_profile_facade
from backend.app.entity_profile.manifests.recruitment import (
    recruitment_candidate_driver_ce_ua_profile,
    recruitment_candidate_warehouse_worker_profile,
    recruitment_module_entity_profiles,
)
from backend.app.entity_profile.mapping_validation import validate_mapping_rules_for_profile
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _bypass_lead_source_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _zero(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_lead_source_limit",
        _noop,
    )
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.count_tenant_lead_sources",
        _zero,
    )
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _noop,
    )


def test_c3_manifests_declare_role_and_country_profiles() -> None:
    codes = {row["profile_code"] for row in recruitment_module_entity_profiles()}
    assert WAREHOUSE_WORKER_PROFILE_CODE in codes
    assert DRIVER_CE_UA_PROFILE_CODE in codes

    warehouse = recruitment_candidate_warehouse_worker_profile()
    ua = recruitment_candidate_driver_ce_ua_profile()
    wh_fields = {row["qualified_code"] for row in warehouse["fields"]}
    ua_fields = {row["qualified_code"] for row in ua["fields"]}

    assert "recruitment.candidate.experience.years_ce" not in wh_fields
    assert "recruitment.candidate.experience.years_ce" in ua_fields
    assert "platform.identity.citizenship" in wh_fields
    assert warehouse["config"]["role_variant"] == "warehouse_worker"
    assert ua["config"]["market_country"] == "PL"
    assert ua["config"]["source_citizenship_default"] == "UA"


@pytest.mark.asyncio
async def test_c3_seed_registers_new_profiles(db, tenant_id: str) -> None:
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    for code in (WAREHOUSE_WORKER_PROFILE_CODE, DRIVER_CE_UA_PROFILE_CODE):
        payload = await resolve_entity_profile_facade(
            db,
            tenant_id=tenant_id,
            entity_profile_code=code,
            include_presentations=True,
        )
        assert payload["bridge_source"] == "entity_profile_registry"
        assert payload["entity_profile_code"] == code
        field_codes = {row["qualified_code"] for row in payload.get("fields") or []}
        assert "platform.identity.citizenship" in field_codes


@pytest.mark.asyncio
async def test_c3_mapping_accepts_profile_fields_rejects_outside(db, tenant_id: str) -> None:
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await db.commit()

    profile_view = await resolve_entity_profile_facade(
        db,
        tenant_id=tenant_id,
        entity_profile_code=WAREHOUSE_WORKER_PROFILE_CODE,
        include_presentations=False,
    )
    allowed = {row["qualified_code"] for row in profile_view.get("fields") or []}
    rules = [
        {
            "source": "first_name",
            "target": "first_name",
            "qualified_field_code": "recruitment.candidate.first_name",
        },
        {
            "source": "citizenship",
            "target": "citizenship",
            "qualified_field_code": "platform.identity.citizenship",
        },
        {
            "source": "years_ce",
            "target": "years_ce",
            "qualified_field_code": "recruitment.candidate.experience.years_ce",
        },
    ]
    result = validate_mapping_rules_for_profile(
        rules,
        allowed_qualified_codes=allowed,
        entity_profile_code=WAREHOUSE_WORKER_PROFILE_CODE,
        resolution_source="tenant_profile",
    )
    assert len(result.accepted_rules) == 2
    assert len(result.rejected_rules) == 1
    assert any("mapping_target_rejected:" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_c3_intake_form_list_includes_new_profiles(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.get("/api/v1/settings/intake-forms/entity-profiles", headers=headers)
    assert resp.status_code == 200, resp.text
    codes = {row["code"] for row in resp.json()}
    assert WAREHOUSE_WORKER_PROFILE_CODE in codes
    assert DRIVER_CE_UA_PROFILE_CODE in codes


@pytest.mark.asyncio
async def test_c3_smoke_warehouse_form_creates_lead_draft(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"c3-wh-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "C3 Warehouse",
            "public_slug": slug,
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
                {"qualified_code": "platform.identity.citizenship", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    form_id = created.json()["form"]["id"]
    smoke = await client.post(f"/api/v1/settings/intake-forms/{form_id}/smoke-test", headers=headers)
    assert smoke.status_code == 200, smoke.text
    body = smoke.json()
    assert body.get("lead_id")
    assert not body.get("candidate_id")

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.stage == "intake_draft"
        count = await session.scalar(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.email == body["contacts"]["email"],
                Candidate.deleted_at.is_(None),
            )
        )
        assert count is None


@pytest.mark.asyncio
async def test_c3_smoke_driver_ce_ua_form_creates_lead_draft(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"c3-ua-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "C3 Driver UA",
            "public_slug": slug,
            "entity_profile_code": DRIVER_CE_UA_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
                {"qualified_code": "platform.identity.citizenship", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["intake_source_profile"]["entity_profile_code"] == DRIVER_CE_UA_PROFILE_CODE

    form_id = created.json()["form"]["id"]
    reject = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "C3 Invalid",
            "public_slug": f"c3-bad-{uuid.uuid4().hex[:8]}",
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.experience.years_ce", "intake_level": "required"},
            ],
        },
    )
    assert reject.status_code == 422, reject.text

    smoke = await client.post(f"/api/v1/settings/intake-forms/{form_id}/smoke-test", headers=headers)
    assert smoke.status_code == 200, smoke.text
    assert smoke.json().get("lead_id")
