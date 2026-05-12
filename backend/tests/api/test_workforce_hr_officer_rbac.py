"""Workforce list/create: HR workspace roles include recruiters."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hr_officer_list_employees_ok(client: AsyncClient, hr_officer_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_hr_officer_create_employee_created(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/workforce/employees",
        headers=hr_officer_headers,
        json={"display_name": "RBAC HR test hire", "status": "onboarding"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data.get("display_name") == "RBAC HR test hire"
    assert data.get("id")


@pytest.mark.asyncio
async def test_recruiter_list_workforce_employees_ok(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
) -> None:
    resp = await client.get("/api/v1/workforce/employees", headers=recruiter_headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
