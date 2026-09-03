"""PR B-1 — questionnaire form list, lead_form_id picker, waiting status on lead."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.modules.leads import crud as leads_crud
from backend.tests.api.test_sales_targeted_advertising_intake import (
    _create_meta_client_lead,
    _seed_sales_profile,
)


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


@pytest.mark.asyncio
async def test_list_questionnaire_forms_for_manager(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    await _seed_sales_profile(tenant_id)

    resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) >= 1
    assert all(row.get("title") for row in rows)
    assert all(row.get("id") for row in rows)


@pytest.mark.asyncio
async def test_questionnaire_invite_sets_waiting_status_and_form_picker(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.app.db.session import async_session_maker

    await _seed_sales_profile(tenant_id)
    forms_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert forms_resp.status_code == 200, forms_resp.text
    picked_form_id = forms_resp.json()[0]["id"]

    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    invite_resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True, "lead_form_id": picked_form_id},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    body = invite_resp.json()
    assert body["status"] == "sent"
    assert body["lead_form_id"] == picked_form_id
    assert body["token"]

    get_resp = await client.get(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["token"] == body["token"]

    async with async_session_maker() as session:
        refreshed = await leads_crud.get_lead(session, tenant_id=tenant_id, lead_id=lead_id)
        assert refreshed is not None
        assert (refreshed.normalized or {}).get("sales_questionnaire_status") == "sent"


@pytest.mark.asyncio
async def test_questionnaire_invite_resend_reuses_same_token(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    await _seed_sales_profile(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    first = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True},
    )
    assert first.status_code == 200, first.text
    first_token = first.json()["token"]

    second = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True},
    )
    assert second.status_code == 200, second.text
    assert second.json()["token"] == first_token
    assert second.json()["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_questionnaire_invite_rejects_foreign_lead_form_id(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.models.tenant_lead_form import TenantLeadForm

    await _seed_sales_profile(tenant_id)
    async with async_session_maker() as session:
        foreign_form = await session.scalar(
            select(TenantLeadForm)
            .where(TenantLeadForm.tenant_id != tenant_id)
            .limit(1)
        )
    foreign_form_id = str(foreign_form.id) if foreign_form is not None else str(uuid4())

    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)

    resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True, "lead_form_id": foreign_form_id},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_questionnaire_invite_rejects_inactive_lead_form(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.models.tenant_lead_form import TenantLeadForm

    await _seed_sales_profile(tenant_id)
    forms_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert forms_resp.status_code == 200, forms_resp.text
    rows = forms_resp.json()
    assert rows
    form_id = next((row["id"] for row in rows if not row.get("is_system_preset")), rows[0]["id"])

    async with async_session_maker() as session:
        form = await session.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.id == form_id,
            )
        )
        assert form is not None
        form.is_active = False
        await session.commit()

    lead = await _create_meta_client_lead(tenant_id)
    lead_id = str(lead.id)
    resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True, "lead_form_id": form_id},
    )
    assert resp.status_code == 422, resp.text

    list_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert list_resp.status_code == 200, list_resp.text
    assert all(row["id"] != form_id for row in list_resp.json())


@pytest.mark.asyncio
async def test_list_questionnaire_forms_excludes_recruitment_profiles(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
    from backend.tests.api.test_intake_forms_settings import _admin_headers

    await _seed_sales_profile(tenant_id)
    admin_headers = await _admin_headers(tenant_id)
    slug = f"recruit-{uuid4().hex[:8]}"
    preset_resp = await client.get(
        f"/api/v1/settings/intake-forms/entity-profiles/{DRIVER_CE_PROFILE_CODE}/presentation-preset",
        headers=admin_headers,
    )
    assert preset_resp.status_code == 200, preset_resp.text
    create_resp = await client.post(
        "/api/v1/settings/intake-forms",
        headers=admin_headers,
        json={
            "title": "Recruitment only form",
            "public_slug": slug,
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": preset_resp.json()["fields"],
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    recruitment_form_id = create_resp.json()["form"]["id"]

    list_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert list_resp.status_code == 200, list_resp.text
    listed_ids = {row["id"] for row in list_resp.json()}
    assert recruitment_form_id not in listed_ids


@pytest.mark.asyncio
async def test_list_and_send_driver_hiring_constructor_form(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.app.entity_profile.constants import DRIVER_HIRING_PROFILE_CODE
    from backend.tests.api.test_intake_forms_settings import _admin_headers

    await _seed_sales_profile(tenant_id)
    admin_headers = await _admin_headers(tenant_id)
    slug = f"company_needs_drivers_{uuid4().hex[:6]}"
    preset_resp = await client.get(
        f"/api/v1/settings/intake-forms/entity-profiles/{DRIVER_HIRING_PROFILE_CODE}/presentation-preset",
        headers=admin_headers,
    )
    assert preset_resp.status_code == 200, preset_resp.text
    create_resp = await client.post(
        "/api/v1/settings/intake-forms",
        headers=admin_headers,
        json={
            "title": "Company needs drivers",
            "public_slug": slug,
            "entity_profile_code": DRIVER_HIRING_PROFILE_CODE,
            "fields": preset_resp.json()["fields"],
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    form_id = created["form"]["id"]
    assert created["form"]["public_slug"] == slug.replace("_", "-")
    assert created["entity_profile"]["code"] == DRIVER_HIRING_PROFILE_CODE

    list_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert list_resp.status_code == 200, list_resp.text
    listed = list_resp.json()
    match = next((row for row in listed if row["id"] == form_id), None)
    assert match is not None
    assert match["target_entity_profile_code"] == DRIVER_HIRING_PROFILE_CODE
    assert listed[0]["id"] == form_id

    lead = await _create_meta_client_lead(tenant_id)
    invite_resp = await client.post(
        f"/api/v1/leads/{lead.id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True, "lead_form_id": form_id},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    body = invite_resp.json()
    assert body["lead_form_id"] == form_id
    assert body["entity_profile_code"] == DRIVER_HIRING_PROFILE_CODE
    assert body["status"] == "sent"
