"""Tenant product modules: recruitment triad + finance (ADR-004)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

from backend.app.api.v1.tenants.service import get_module_settings_snapshot


def test_recruitment_snapshot_matches_triad() -> None:
    tenant = SimpleNamespace(
        settings={"modules": {"candidates": True, "leads": True, "vacancies": False, "finance": False}}
    )
    m = get_module_settings_snapshot(tenant)  # type: ignore[arg-type]
    assert m["recruitment"] is False
    assert m["finance"] is False


async def test_patch_recruitment_syncs_triad(client: AsyncClient, manager_headers: dict) -> None:
    on = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"recruitment": True},
    )
    assert on.status_code == 200, on.text
    body = on.json()
    assert body["candidates"] is True
    assert body["leads"] is True
    assert body["vacancies"] is True
    assert body["recruitment"] is True

    off = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"recruitment": False},
    )
    assert off.status_code == 200, off.text
    b2 = off.json()
    assert b2["candidates"] is False
    assert b2["leads"] is False
    assert b2["vacancies"] is False
    assert b2["recruitment"] is False

    restore = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"candidates": True, "leads": True, "vacancies": True},
    )
    assert restore.status_code == 200, restore.text
