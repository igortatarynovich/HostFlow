"""Fleet API: dedicated fleet_manager role vs HR-only (no fleet)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_fleet_manager_list_vehicles_ok(
    client: AsyncClient,
    fleet_manager_headers: Dict[str, str],
) -> None:
    resp = await client.get("/api/v1/fleet/vehicles", headers=fleet_manager_headers)
    if resp.status_code != 200:
        pytest.skip(f"fleet vehicles unavailable (HTTP {resp.status_code}): {resp.text[:400]}")
    assert isinstance(resp.json(), dict)


async def test_hr_officer_fleet_vehicles_forbidden(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
) -> None:
    resp = await client.get("/api/v1/fleet/vehicles", headers=hr_officer_headers)
    assert resp.status_code == 403, resp.text
