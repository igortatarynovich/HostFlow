"""Fleet operating lines CRUD (tenant-scoped)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_fleet_status_ok(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/fleet/status", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("module") == "fleet"


async def test_fleet_operating_lines_roundtrip(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    list_empty = await client.get("/api/v1/fleet/operating-lines", headers=manager_headers)
    if list_empty.status_code == 500 and "fleet_operating_lines" in list_empty.text:
        pytest.skip("fleet_operating_lines table not migrated in this database")
    assert list_empty.status_code == 200, list_empty.text

    name = "pytest-fleet-line-001"
    created = await client.post(
        "/api/v1/fleet/operating-lines",
        headers=manager_headers,
        json={"name": name, "status": "active"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    line_id = body["id"]
    assert body["name"] == name
    assert body.get("status") == "active"

    one = await client.get(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
    assert one.status_code == 200, one.text
    assert one.json()["id"] == line_id

    factors = [1.0] * 12
    patched = await client.patch(
        f"/api/v1/fleet/operating-lines/{line_id}",
        headers=manager_headers,
        json={"seasonality_month_factors": factors},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json().get("seasonality_month_factors") == factors

    bad = await client.patch(
        f"/api/v1/fleet/operating-lines/{line_id}",
        headers=manager_headers,
        json={"seasonality_month_factors": [1.0] * 11},
    )
    assert bad.status_code == 400, bad.text

    deleted = await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
    assert deleted.status_code == 204, deleted.text

    gone = await client.get(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
    assert gone.status_code == 404, gone.text
