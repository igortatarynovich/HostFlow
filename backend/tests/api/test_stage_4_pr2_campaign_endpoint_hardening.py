"""Stage 4 PR-2 — Campaign status discipline + Endpoint PATCH parity."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.activity import list_activity_events
from backend.app.db.session import async_session_maker
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data, _set_tenant


async def _default_own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc
        return str(oc)


async def _seed_form(*, tenant_id: str) -> str:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title=f"Form {form_id[:6]}",
                public_slug=f"form-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
            )
        )
        await session.commit()
    return form_id


async def _create_campaign(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=headers,
        json={
            "name": f"PR2 {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "targets": [],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_emits_campaign_created(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    camp = await _create_campaign(client, auth_headers)
    campaign_id = camp["id"]

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        events = await list_activity_events(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            limit=50,
        )
    types = [e.event_type for e in events]
    assert "CampaignCreated" in types
    assert "FlightCreated" in types
    created = next(e for e in events if e.event_type == "CampaignCreated")
    assert created.source_event_id == f"acq.campaign.created:{campaign_id}"


@pytest.mark.asyncio
async def test_campaign_status_patch_forbidden(
    client: AsyncClient, auth_headers: dict
) -> None:
    await _init_data()
    camp = await _create_campaign(client, auth_headers)
    campaign_id = camp["id"]

    forbidden = await client.patch(
        f"/api/v1/platform/campaigns/{campaign_id}",
        headers=auth_headers,
        json={"status": "active"},
    )
    assert forbidden.status_code == 422, forbidden.text
    assert "status" in forbidden.text.lower() or "complete" in forbidden.text.lower()

    meta = await client.patch(
        f"/api/v1/platform/campaigns/{campaign_id}",
        headers=auth_headers,
        json={"name": "Renamed PR2 campaign"},
    )
    assert meta.status_code == 200, meta.text
    assert meta.json()["name"] == "Renamed PR2 campaign"
    assert meta.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_complete_and_archive_commands(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    camp = await _create_campaign(client, auth_headers)
    campaign_id = camp["id"]

    completed = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/complete",
        headers=auth_headers,
        json={"reason": "won"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    # Flight untouched by Campaign complete
    assert completed.json()["flights"][0]["status"] == "planned"

    again = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/complete",
        headers=auth_headers,
        json={},
    )
    assert again.status_code == 200, again.text
    assert again.json()["status"] == "completed"

    archived = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/archive",
        headers=auth_headers,
        json={},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        events = await list_activity_events(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            limit=50,
        )
    types = {e.event_type for e in events}
    assert "CampaignCompleted" in types
    assert "CampaignArchived" in types


@pytest.mark.asyncio
async def test_flight_scoped_form_link_patch(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}

    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]

    attached = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/forms",
        headers=headers,
        json={"form_id": form_id, "role": "primary"},
    )
    assert attached.status_code == 201, attached.text
    link_id = attached.json()["flights"][0]["forms"][0]["id"]
    assert attached.json()["flights"][0]["forms"][0]["is_active"] is True

    patched = await client.patch(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/forms/{link_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert patched.status_code == 200, patched.text
    forms = patched.json()["flights"][0]["forms"]
    assert len(forms) == 1
    assert forms[0]["id"] == link_id
    assert forms[0]["is_active"] is False
