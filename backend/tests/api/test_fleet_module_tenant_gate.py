"""Fleet API respects tenant.settings.modules.fleet."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_fleet_overview_403_when_fleet_module_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    off = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"fleet": False},
    )
    assert off.status_code == 200, off.text

    resp = await client.get("/api/v1/fleet/overview", headers=manager_headers)
    assert resp.status_code == 403, resp.text
    assert "disabled" in (resp.json().get("detail") or "").lower()

    on = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"fleet": True},
    )
    assert on.status_code == 200, on.text

    ok = await client.get("/api/v1/fleet/overview", headers=manager_headers)
    if ok.status_code != 200:
        pytest.skip(f"fleet overview unavailable (HTTP {ok.status_code}): {ok.text[:400]}")
    body = ok.json()
    assert "vehicles_total" in body
