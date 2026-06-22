"""P9 — Mapping UI / Provider Bindings."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_intake_demo_form import ensure_tenant_default_driver_ce_intake_form
from backend.tests.api.test_intake_forms_settings import _admin_headers


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _bypass_lead_source_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _zero(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr("backend.app.services.intake_form_write_service.ensure_lead_source_limit", _noop)
    monkeypatch.setattr("backend.app.services.intake_form_write_service.count_tenant_lead_sources", _zero)
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _noop,
    )


async def _seed_driver_ce(tenant_id: str) -> str:
    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_tenant_default_driver_ce_intake_form(session, tenant_id)
        await session.commit()
        from sqlalchemy import select
        from backend.app.models.tenant_lead_form import TenantLeadForm
        from backend.app.entity_profile.seed_intake_demo_form import DRIVER_CE_FORM_SLUG

        form = await session.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.public_slug == DRIVER_CE_FORM_SLUG,
            )
        )
        assert form is not None
        return str(form.id)


@pytest.mark.asyncio
async def test_p9_get_mapping_context(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.get(f"/api/v1/settings/intake-forms/{form_id}/mapping", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert body["provider"] == "public_intake"
    assert body["intake_source_profile_id"]
    assert isinstance(body["provider_bindings"], list)


@pytest.mark.asyncio
async def test_p9_save_valid_mapping_and_preview(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce(tenant_id)
    headers = await _admin_headers(tenant_id)
    rules = [
        {
            "source": "first_name",
            "qualified_field_code": "recruitment.candidate.first_name",
            "format": "string",
        },
        {
            "source": "phone_number",
            "qualified_field_code": "recruitment.candidate.contacts.phone",
            "format": "string",
        },
    ]
    put = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/mapping",
        headers=headers,
        json={"mapping_rules": rules},
    )
    assert put.status_code == 200, put.text
    assert len(put.json()["mapping_rules"]) == 2

    sample = {
        "first_name": "Anna",
        "phone_number": "+48123456789",
        "email": "anna@example.com",
    }
    preview = await client.post(
        f"/api/v1/settings/intake-forms/{form_id}/mapping/preview",
        headers=headers,
        json={"sample_payload": sample},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["normalized_payload"].get("first_name") == "Anna"
    assert body["mapping_validation"]["accepted_count"] == 2
    assert body["ingest_envelope_v1"]["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert "raw_payload_v1" in body["normalized_payload"]


@pytest.mark.asyncio
async def test_p9_rejects_mapping_target_outside_profile(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/mapping",
        headers=headers,
        json={
            "mapping_rules": [
                {
                    "source": "company_name",
                    "qualified_field_code": "recruitment.client.company.name",
                }
            ]
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") in {"mapping_target_not_in_profile", "mapping_entity_type_mismatch"}


@pytest.mark.asyncio
async def test_p9_test_ingest_creates_lead_draft(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce(tenant_id)
    headers = await _admin_headers(tenant_id)
    rules = [
        {
            "source": "full_name",
            "qualified_field_code": "recruitment.candidate.first_name",
        },
        {
            "source": "mobile",
            "qualified_field_code": "recruitment.candidate.contacts.phone",
        },
    ]
    await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/mapping",
        headers=headers,
        json={"mapping_rules": rules},
    )
    sample = {"full_name": "Jan", "mobile": "+48987654321"}
    resp = await client.post(
        f"/api/v1/settings/intake-forms/{form_id}/mapping/test-ingest",
        headers=headers,
        json={"sample_payload": sample},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lead_id"]
    assert not body.get("candidate_id")
    assert body["normalized_payload"].get("first_name") == "Jan"
    assert body["ingest_envelope_v1"]["mapping_result"]["accepted_count"] >= 1


@pytest.mark.asyncio
async def test_p9_provider_agnostic_source_fields(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce(tenant_id)
    headers = await _admin_headers(tenant_id)
    sample = {f"field_{uuid.uuid4().hex[:4]}": "value-a", "custom_phone": "+48111222333"}
    preview = await client.post(
        f"/api/v1/settings/intake-forms/{form_id}/mapping/preview",
        headers=headers,
        json={
            "sample_payload": sample,
            "mapping_rules": [
                {
                    "source": "custom_phone",
                    "qualified_field_code": "recruitment.candidate.contacts.phone",
                }
            ],
        },
    )
    assert preview.status_code == 200, preview.text
    names = {row["source"] for row in preview.json()["source_fields"]}
    assert "custom_phone" in names
