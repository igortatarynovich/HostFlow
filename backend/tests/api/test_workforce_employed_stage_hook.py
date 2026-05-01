"""Workforce row auto-created when candidate reaches employment_pending or employed."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_patch_candidate_to_employed_creates_workforce_row(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "employed"},
    )
    assert patch.status_code == 200, patch.text

    employees = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    assert employees.status_code == 200, employees.text
    rows = employees.json()
    linked = [r for r in rows if r.get("candidate_id") == candidate_id]
    assert len(linked) == 1
    assert linked[0].get("display_name")


@pytest.mark.asyncio
async def test_patch_candidate_to_employment_pending_creates_workforce_row(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "employment_pending"},
    )
    assert patch.status_code == 200, patch.text

    employees = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    assert employees.status_code == 200, employees.text
    rows = employees.json()
    linked = [r for r in rows if r.get("candidate_id") == candidate_id]
    assert len(linked) == 1


@pytest.mark.asyncio
async def test_patch_candidate_stays_employment_pending_idempotent_workforce(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    """Handoff runs once; repeating the same stage must not create duplicate workforce rows."""
    for _ in range(2):
        patch = await client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=manager_headers,
            json={"stage": "employment_pending"},
        )
        assert patch.status_code == 200, patch.text

    employees = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    rows = employees.json()
    linked = [r for r in rows if r.get("candidate_id") == candidate_id]
    assert len(linked) == 1


@pytest.mark.asyncio
async def test_patch_candidate_stays_employed_idempotent_workforce(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    for _ in range(2):
        patch = await client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=manager_headers,
            json={"stage": "employed"},
        )
        assert patch.status_code == 200, patch.text

    employees = await client.get("/api/v1/workforce/employees", headers=manager_headers)
    rows = employees.json()
    linked = [r for r in rows if r.get("candidate_id") == candidate_id]
    assert len(linked) == 1
