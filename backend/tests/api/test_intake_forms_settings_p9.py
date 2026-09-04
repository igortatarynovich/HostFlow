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


def test_intake_form_mapping_put_code_is_leftover_writer() -> None:
    from fastapi import HTTPException

    from backend.app.acquisition.mapping_leftover_writers import (
        INTAKE_FORM_MAPPING_WRITES_RETIRED,
        raise_intake_form_mapping_writes_retired,
    )

    try:
        raise_intake_form_mapping_writes_retired(
            mapping_path="/app/marketing/sources/src-1/mapping",
        )
    except HTTPException as exc:
        assert exc.status_code == 410
        assert exc.detail["code"] == INTAKE_FORM_MAPPING_WRITES_RETIRED
        assert exc.detail["mapping_path"] == "/app/marketing/sources/src-1/mapping"
    else:
        raise AssertionError("expected leftover writer 410")


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
async def test_p9_intake_mapping_put_is_leftover_writer(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce(tenant_id)
    headers = await _admin_headers(tenant_id)
    put = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/mapping",
        headers=headers,
        json={
            "mapping_rules": [
                {
                    "source": "first_name",
                    "qualified_field_code": "recruitment.candidate.first_name",
                    "format": "string",
                }
            ]
        },
    )
    assert put.status_code == 410, put.text
    detail = put.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "intake_form_mapping_writes_retired"
    assert "/app/marketing/sources/" in str(detail.get("mapping_path") or "")


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
    assert put.status_code == 410, put.text

    sample = {
        "first_name": "Anna",
        "phone_number": "+48123456789",
        "email": "anna@example.com",
    }
    preview = await client.post(
        f"/api/v1/settings/intake-forms/{form_id}/mapping/preview",
        headers=headers,
        json={"sample_payload": sample, "mapping_rules": rules},
    )
    assert preview.status_code == 422, preview.text
    detail = preview.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "intake_form_mapping_preview_uses_saved_contract"
    assert "/app/marketing/sources" in str(detail.get("mapping_path") or "")

    saved_preview = await client.post(
        f"/api/v1/settings/intake-forms/{form_id}/mapping/preview",
        headers=headers,
        json={"sample_payload": sample},
    )
    assert saved_preview.status_code == 200, saved_preview.text
    body = saved_preview.json()
    assert "normalized_payload" in body
    assert body["ingest_envelope_v1"]["mapping_rules_source"]


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
    assert resp.status_code == 410, resp.text
    detail = resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "intake_form_mapping_writes_retired"


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
    put = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/mapping",
        headers=headers,
        json={"mapping_rules": rules},
    )
    assert put.status_code == 410, put.text
    sample = {"full_name": "Jan", "mobile": "+48987654321"}
    resp = await client.post(
        f"/api/v1/settings/intake-forms/{form_id}/mapping/test-ingest",
        headers=headers,
        json={"sample_payload": sample, "mapping_rules": rules},
    )
    assert resp.status_code == 410, resp.text
    detail = resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "intake_form_mapping_evaluator_retired"
    assert "/app/marketing/sources" in str(detail.get("mapping_path") or "")


@pytest.mark.asyncio
async def test_p9_provider_agnostic_source_fields(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce(tenant_id)
    headers = await _admin_headers(tenant_id)
    sample = {f"field_{uuid.uuid4().hex[:4]}": "value-a", "custom_phone": "+48111222333"}
    preview = await client.post(
        f"/api/v1/settings/intake-forms/{form_id}/mapping/preview",
        headers=headers,
        json={"sample_payload": sample},
    )
    assert preview.status_code == 200, preview.text
    names = {row["source"] for row in preview.json()["source_fields"]}
    assert "custom_phone" in names
