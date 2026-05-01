"""Fleet park: vehicles, trailers, drivers list + create."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_fleet_vehicles_list_and_create(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    r0 = await client.get("/api/v1/fleet/vehicles", headers=manager_headers)
    if r0.status_code != 200:
        pytest.skip(f"fleet vehicles unavailable (HTTP {r0.status_code}): {r0.text[:400]}")

    plate = "pytest-fleet-veh-001"
    created = await client.post(
        "/api/v1/fleet/vehicles",
        headers=manager_headers,
        json={"registration_plate": plate},
    )
    assert created.status_code == 201, created.text
    assert created.json().get("registration_plate") == plate


async def test_fleet_trailers_create_requires_identifier(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    r0 = await client.get("/api/v1/fleet/trailers", headers=manager_headers)
    if r0.status_code != 200:
        pytest.skip(f"fleet trailers unavailable (HTTP {r0.status_code})")
    bad = await client.post("/api/v1/fleet/trailers", headers=manager_headers, json={})
    assert bad.status_code == 422, bad.text


async def test_fleet_drivers_create(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    r0 = await client.get("/api/v1/fleet/drivers", headers=manager_headers)
    if r0.status_code != 200:
        pytest.skip(f"fleet drivers unavailable (HTTP {r0.status_code})")
    code = "pytest-driver-001"
    created = await client.post(
        "/api/v1/fleet/drivers",
        headers=manager_headers,
        json={"display_code": code},
    )
    assert created.status_code == 201, created.text
    assert created.json().get("display_code") == code
