"""Seasonality profile from assignment history (not manual line factors)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _skip_if_no_fleet_tables(resp) -> None:
    if resp.status_code == 500 and "fleet" in resp.text.lower():
        pytest.skip("fleet tables not available in this database")


async def test_seasonality_from_data_insufficient_without_assignments(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    listed = await client.get("/api/v1/fleet/operating-lines", headers=manager_headers)
    await _skip_if_no_fleet_tables(listed)
    assert listed.status_code == 200, listed.text

    created = await client.post(
        "/api/v1/fleet/operating-lines",
        headers=manager_headers,
        json={"name": "pytest-seasonality-empty", "status": "active"},
    )
    assert created.status_code == 201, created.text
    line_id = created.json()["id"]

    sea = await client.get(
        f"/api/v1/fleet/operating-lines/{line_id}/seasonality-from-data",
        headers=manager_headers,
        params={"months_back": 12},
    )
    assert sea.status_code == 200, sea.text
    body = sea.json()
    assert body["insufficient_data"] is True
    assert body["months_1_to_12"] == [1.0] * 12
    assert body["source"] == "assignments"

    await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)


async def test_seasonality_from_data_normalized_weights(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    listed = await client.get("/api/v1/fleet/operating-lines", headers=manager_headers)
    await _skip_if_no_fleet_tables(listed)
    assert listed.status_code == 200, listed.text

    line = await client.post(
        "/api/v1/fleet/operating-lines",
        headers=manager_headers,
        json={"name": "pytest-seasonality-filled", "status": "active"},
    )
    assert line.status_code == 201, line.text
    line_id = line.json()["id"]

    veh = await client.post(
        "/api/v1/fleet/vehicles",
        headers=manager_headers,
        json={"status": "active"},
    )
    if veh.status_code != 201:
        await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
        pytest.skip(f"fleet vehicles not available: {veh.status_code} {veh.text}")

    vehicle_id = veh.json()["id"]

    today = date.today()
    start = today - timedelta(days=400)
    end = today

    asn = await client.post(
        "/api/v1/fleet/assignments",
        headers=manager_headers,
        json={
            "line_id": line_id,
            "vehicle_id": vehicle_id,
            "status": "planned",
            "service_start": start.isoformat(),
            "service_end": end.isoformat(),
        },
    )
    assert asn.status_code == 201, asn.text
    assignment_id = asn.json()["id"]

    sea = await client.get(
        f"/api/v1/fleet/operating-lines/{line_id}/seasonality-from-data",
        headers=manager_headers,
        params={"months_back": 24},
    )
    assert sea.status_code == 200, sea.text
    body = sea.json()
    assert body["insufficient_data"] is False
    fac = body["months_1_to_12"]
    assert len(fac) == 12
    assert abs(sum(fac) - 12.0) < 0.02

    await client.delete(f"/api/v1/fleet/assignments/{assignment_id}", headers=manager_headers)
    await client.delete(f"/api/v1/fleet/vehicles/{vehicle_id}", headers=manager_headers)
    await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)


async def test_seasonality_roster_source_vehicle_membership(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    listed = await client.get("/api/v1/fleet/operating-lines", headers=manager_headers)
    await _skip_if_no_fleet_tables(listed)
    assert listed.status_code == 200, listed.text

    line = await client.post(
        "/api/v1/fleet/operating-lines",
        headers=manager_headers,
        json={"name": "pytest-seasonality-roster", "status": "active"},
    )
    assert line.status_code == 201, line.text
    line_id = line.json()["id"]

    veh = await client.post(
        "/api/v1/fleet/vehicles",
        headers=manager_headers,
        json={"status": "active"},
    )
    if veh.status_code != 201:
        await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
        pytest.skip(f"fleet vehicles not available: {veh.status_code} {veh.text}")
    vehicle_id = veh.json()["id"]

    mem = await client.post(
        f"/api/v1/fleet/operating-lines/{line_id}/vehicles",
        headers=manager_headers,
        json={"vehicle_id": vehicle_id},
    )
    assert mem.status_code == 201, mem.text
    membership_id = mem.json()["id"]

    sea = await client.get(
        f"/api/v1/fleet/operating-lines/{line_id}/seasonality-from-data",
        headers=manager_headers,
        params={"months_back": 12, "sources": "roster"},
    )
    assert sea.status_code == 200, sea.text
    body = sea.json()
    assert body["source"] == "roster"
    assert body["insufficient_data"] is False
    assert abs(sum(body["months_1_to_12"]) - 12.0) < 0.02

    await client.delete(
        f"/api/v1/fleet/operating-lines/{line_id}/vehicles/{membership_id}",
        headers=manager_headers,
    )
    await client.delete(f"/api/v1/fleet/vehicles/{vehicle_id}", headers=manager_headers)
    await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)


async def test_seasonality_blend_assignments_and_roster(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    listed = await client.get("/api/v1/fleet/operating-lines", headers=manager_headers)
    await _skip_if_no_fleet_tables(listed)
    assert listed.status_code == 200, listed.text

    line = await client.post(
        "/api/v1/fleet/operating-lines",
        headers=manager_headers,
        json={"name": "pytest-seasonality-blend", "status": "active"},
    )
    assert line.status_code == 201, line.text
    line_id = line.json()["id"]

    veh = await client.post(
        "/api/v1/fleet/vehicles",
        headers=manager_headers,
        json={"status": "active"},
    )
    if veh.status_code != 201:
        await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
        pytest.skip(f"fleet vehicles not available: {veh.status_code} {veh.text}")
    vehicle_id = veh.json()["id"]

    mem = await client.post(
        f"/api/v1/fleet/operating-lines/{line_id}/vehicles",
        headers=manager_headers,
        json={"vehicle_id": vehicle_id},
    )
    assert mem.status_code == 201, mem.text
    membership_id = mem.json()["id"]

    today = date.today()
    start = today - timedelta(days=120)
    asn = await client.post(
        "/api/v1/fleet/assignments",
        headers=manager_headers,
        json={
            "line_id": line_id,
            "vehicle_id": vehicle_id,
            "status": "planned",
            "service_start": start.isoformat(),
            "service_end": today.isoformat(),
        },
    )
    assert asn.status_code == 201, asn.text
    assignment_id = asn.json()["id"]

    sea = await client.get(
        f"/api/v1/fleet/operating-lines/{line_id}/seasonality-from-data",
        headers=manager_headers,
        params={
            "months_back": 12,
            "sources": "assignments,roster",
            "weight_assignments": 0.5,
            "weight_roster": 0.5,
        },
    )
    assert sea.status_code == 200, sea.text
    body = sea.json()
    assert body["source"] == "blend"
    assert body["blend_weights"] == {"assignments": 0.5, "roster": 0.5}
    assert body["insufficient_data"] is False
    assert abs(sum(body["months_1_to_12"]) - 12.0) < 0.02

    await client.delete(f"/api/v1/fleet/assignments/{assignment_id}", headers=manager_headers)
    await client.delete(
        f"/api/v1/fleet/operating-lines/{line_id}/vehicles/{membership_id}",
        headers=manager_headers,
    )
    await client.delete(f"/api/v1/fleet/vehicles/{vehicle_id}", headers=manager_headers)
    await client.delete(f"/api/v1/fleet/operating-lines/{line_id}", headers=manager_headers)
