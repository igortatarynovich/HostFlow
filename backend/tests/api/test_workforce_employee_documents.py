"""Smoke tests for HR workforce employee documents (CandDoc via candidate link)."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hr_officer_documents_empty_without_candidate(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=hr_officer_headers,
        json={
            "display_name": "WF docs — no candidate",
            "status": "active",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    res = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/documents",
        headers=hr_officer_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json() == []


@pytest.mark.asyncio
async def test_hr_officer_documents_ok_with_candidate(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    cid = candidate_id
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=hr_officer_headers,
        json={
            "display_name": "WF docs — with candidate",
            "status": "active",
            "company_id": bootstrap["company_id"],
            "candidate_id": cid,
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    res = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/documents",
        headers=hr_officer_headers,
    )
    assert res.status_code == 200, res.text
    body: list[Any] = res.json()
    assert isinstance(body, list)
    for row in body:
        assert "id" in row
        assert row.get("candidate_id") == cid
        assert "doc_type" in row


@pytest.mark.asyncio
async def test_recruiter_forbidden_employee_documents(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=recruiter_headers,
        json={"display_name": "should fail", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 403, create.text

    ok = await client.post(
        "/api/v1/workforce/employees",
        headers=hr_officer_headers,
        json={
            "display_name": "WF recruiter ACL",
            "company_id": bootstrap["company_id"],
            "candidate_id": candidate_id,
        },
    )
    assert ok.status_code == 201, ok.text
    emp_id = ok.json()["id"]

    res = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/documents",
        headers=recruiter_headers,
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_hr_officer_documents_404_unknown_employee(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
) -> None:
    res = await client.get(
        "/api/v1/workforce/employees/00000000-0000-4000-8000-000000000099/documents",
        headers=hr_officer_headers,
    )
    assert res.status_code == 404
