"""Fleet work-models list/create (rotation templates)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_fleet_work_models_list_ok(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    r = await client.get("/api/v1/fleet/work-models", headers=manager_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)


async def test_fleet_work_models_create_and_roundtrip(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    r0 = await client.get("/api/v1/fleet/work-models", headers=manager_headers)
    if r0.status_code != 200:
        pytest.skip(f"fleet work-models unavailable (HTTP {r0.status_code}): {r0.text[:400]}")
    name = "pytest-wm-001"
    created = await client.post(
        "/api/v1/fleet/work-models",
        headers=manager_headers,
        json={"name": name, "work_days": 5, "rest_days": 2, "cycle_length": 7},
    )
    assert created.status_code == 201, created.text
    wid = created.json().get("id")
    assert wid
    one = await client.get(f"/api/v1/fleet/work-models/{wid}", headers=manager_headers)
    assert one.status_code == 200, one.text
    assert one.json().get("name") == name
