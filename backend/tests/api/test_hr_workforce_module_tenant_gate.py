"""Workforce API respects tenant.settings.modules.hr."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_workforce_employees_403_when_hr_module_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    off = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": False},
    )
    assert off.status_code == 200, off.text

    resp = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    assert resp.status_code == 403, resp.text
    assert "disabled" in (resp.json().get("detail") or "").lower()

    on = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    assert on.status_code == 200, on.text

    ok = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    assert ok.status_code == 200, ok.text
