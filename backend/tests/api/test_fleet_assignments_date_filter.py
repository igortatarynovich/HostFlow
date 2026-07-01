"""Fleet assignments list: service_from / service_to overlap filter."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_fleet_assignments_filtered_by_service_window(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    lines_r = await client.get("/api/v1/fleet/operating-lines", headers=manager_headers)
    if lines_r.status_code != 200:
        pytest.skip(f"fleet operating lines unavailable: HTTP {lines_r.status_code}")
    veh_r = await client.get("/api/v1/fleet/vehicles", headers=manager_headers)
    if veh_r.status_code != 200:
        pytest.skip(f"fleet vehicles unavailable: HTTP {veh_r.status_code}")

    line = await client.post(
        "/api/v1/fleet/operating-lines",
        headers=manager_headers,
        json={"name": "pytest-assign-window-line", "status": "active"},
    )
    assert line.status_code == 201, line.text
    line_id = line.json()["id"]

    vehicle = await client.post(
        "/api/v1/fleet/vehicles",
        headers=manager_headers,
        json={"registration_plate": "pytest-assign-win-veh", "status": "active"},
    )
    assert vehicle.status_code == 201, vehicle.text
    vehicle_id = vehicle.json()["id"]

    june = await client.post(
        "/api/v1/fleet/assignments",
        headers=manager_headers,
        json={
            "line_id": line_id,
            "vehicle_id": vehicle_id,
            "status": "planned",
            "service_start": "2026-06-10",
            "service_end": "2026-06-12",
        },
    )
    assert june.status_code == 201, june.text
    june_id = june.json()["id"]

    august = await client.post(
        "/api/v1/fleet/assignments",
        headers=manager_headers,
        json={
            "line_id": line_id,
            "vehicle_id": vehicle_id,
            "status": "planned",
            "service_start": "2026-08-01",
        },
    )
    assert august.status_code == 201, august.text
    august_id = august.json()["id"]

    try:
        base = "/api/v1/fleet/assignments"

        async def fetch_ids(params: Dict[str, str]) -> set[str]:
            r = await client.get(base, headers=manager_headers, params=params)
            assert r.status_code == 200, r.text
            return {item["id"] for item in r.json().get("items", [])}

        june_only = await fetch_ids({"service_from": "2026-06-01", "service_to": "2026-06-30"})
        assert june_id in june_only
        assert august_id not in june_only

        august_only = await fetch_ids({"service_from": "2026-08-01", "service_to": "2026-08-31"})
        assert august_id in august_only
        assert june_id not in august_only

        gap = await fetch_ids({"service_from": "2026-07-01", "service_to": "2026-07-31"})
        assert june_id not in gap
        assert august_id not in gap

        all_rows = await fetch_ids({})
        assert june_id in all_rows and august_id in all_rows
    finally:
        await client.delete(f"/api/v1/fleet/assignments/{june_id}", headers=manager_headers)
        await client.delete(f"/api/v1/fleet/assignments/{august_id}", headers=manager_headers)
        await client.delete(f"/api/v1/fleet/vehicles/{vehicle_id}", headers=manager_headers)
        await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
