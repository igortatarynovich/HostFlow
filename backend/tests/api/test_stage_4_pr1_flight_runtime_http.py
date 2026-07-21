"""Stage 4 PR-1 — Flight Runtime HTTP commands + metadata PATCH."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from backend.tests.conftest import _init_data


async def _create_campaign(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=headers,
        json={
            "name": f"Runtime {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "targets": [],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert len(body["flights"]) == 1
    assert body["flights"][0]["status"] == "planned"
    return body


@pytest.mark.asyncio
async def test_http_launch_pause_resume_complete(
    client: AsyncClient, auth_headers: dict
) -> None:
    await _init_data()
    camp = await _create_campaign(client, auth_headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]

    launched = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/launch",
        headers=auth_headers,
        json={"reason": "go-live"},
    )
    assert launched.status_code == 200, launched.text
    body = launched.json()
    assert body["command"] == "launch"
    assert body["flight_status"] == "active"
    assert body["campaign_status"] == "active"
    assert body["flight_event_type"] == "FlightStarted"
    assert body["campaign_event_type"] == "CampaignActivated"

    paused = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/pause",
        headers=auth_headers,
        json={},
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["flight_status"] == "paused"
    assert paused.json()["campaign_status"] == "paused"
    assert paused.json()["campaign_event_type"] == "CampaignPaused"

    resumed = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/resume",
        headers=auth_headers,
        json={},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["flight_status"] == "active"
    assert resumed.json()["campaign_status"] == "active"

    completed = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/complete",
        headers=auth_headers,
        json={},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["flight_status"] == "completed"
    assert completed.json()["campaign_status"] == "active"
    assert completed.json()["campaign_event_type"] is None


@pytest.mark.asyncio
async def test_http_illegal_transition_and_status_patch_forbidden(
    client: AsyncClient, auth_headers: dict
) -> None:
    await _init_data()
    camp = await _create_campaign(client, auth_headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]

    bad = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/pause",
        headers=auth_headers,
        json={},
    )
    assert bad.status_code == 422

    patch_status = await client.patch(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}",
        headers=auth_headers,
        json={"status": "active"},
    )
    assert patch_status.status_code == 422

    meta = await client.patch(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}",
        headers=auth_headers,
        json={"name": "Wave A"},
    )
    assert meta.status_code == 200, meta.text
    assert meta.json()["name"] == "Wave A"
    assert meta.json()["status"] == "planned"

    listed = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == flight_id


@pytest.mark.asyncio
async def test_http_launch_idempotent(client: AsyncClient, auth_headers: dict) -> None:
    await _init_data()
    camp = await _create_campaign(client, auth_headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]

    first = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/launch",
        headers=auth_headers,
        json={},
    )
    second = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/launch",
        headers=auth_headers,
        json={},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["flight_event_id"] == second.json()["flight_event_id"]
    assert second.json()["campaign_event_id"] is None
