"""HR Employees Directory read-model (GET /workforce/employees/directory)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_directory_hr_officer_ok_shape(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
) -> None:
    resp = await client.get("/api/v1/workforce/employees/directory", headers=hr_officer_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body and "total" in body
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    if body["items"]:
        row = body["items"][0]
        for k in (
            "employee_id",
            "full_name",
            "status",
            "compliance_status",
            "missing_documents_count",
            "expiring_documents_count",
            "risk_level",
        ):
            assert k in row, row


@pytest.mark.asyncio
async def test_directory_recruiter_forbidden(client: AsyncClient, recruiter_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/employees/directory", headers=recruiter_headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_directory_viewer_forbidden(client: AsyncClient, viewer_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/employees/directory", headers=viewer_headers)
    assert resp.status_code == 403, resp.text
