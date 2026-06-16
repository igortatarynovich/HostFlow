"""Contract tests: recruiter role vs `/api/v1/workforce/*` (CI before prod deploy).

Fails fast if the workforce router is not mounted (404) or RBAC excludes recruiter (403).
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workforce_router_mounted_not_404(client: AsyncClient, recruiter_headers: Dict[str, str]) -> None:
    """Regression: forgot ``include_router(workforce_router)`` in ``main.py`` → 404."""
    resp = await client.get("/api/v1/workforce/employees", headers=recruiter_headers)
    assert resp.status_code != 404, resp.text


@pytest.mark.asyncio
async def test_recruiter_list_employees_forbidden(client: AsyncClient, recruiter_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/employees", headers=recruiter_headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_hr_officer_list_employees_shape(client: AsyncClient, hr_officer_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    for row in body[:3]:
        assert "id" in row
        assert "tenant_id" in row
        assert "display_name" in row
        assert "status" in row


@pytest.mark.asyncio
async def test_recruiter_create_get_patch_employee(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "Contract recruiter employee",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    data = create.json()
    assert data.get("display_name") == "Contract recruiter employee"
    emp_id = data["id"]
    assert data.get("tenant_id")

    one = await client.get(f"/api/v1/workforce/employees/{emp_id}", headers=hr_officer_headers)
    assert one.status_code == 200, one.text
    assert one.json()["id"] == emp_id

    patched = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}",
        headers=h,
        json={"notes": "contract patch"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json().get("notes") == "contract patch"


@pytest.mark.asyncio
async def test_recruiter_hr_bundle_shape(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={"display_name": "HR bundle shape", "status": "active", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    res = await client.get(f"/api/v1/workforce/employees/{emp_id}/hr-bundle", headers=hr_officer_headers)
    assert res.status_code == 200, res.text
    bundle: Dict[str, Any] = res.json()
    assert set(bundle.keys()) >= {
        "employments",
        "payroll_profile",
        "zus_profile",
        "onboarding_tasks",
        "absences",
        "leave_requests",
        "work_eligibility_payment_requirements",
    }
    assert isinstance(bundle["employments"], list)
    assert isinstance(bundle["onboarding_tasks"], list)


@pytest.mark.asyncio
async def test_recruiter_link_user_options_shape(client: AsyncClient, hr_officer_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/employees/link-user-options", headers=hr_officer_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert isinstance(rows, list)
    for row in rows[:5]:
        assert "user_id" in row
        assert "email" in row


@pytest.mark.asyncio
async def test_recruiter_employee_documents_with_candidate(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    cid = candidate_id
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "Docs via candidate",
            "status": "active",
            "company_id": bootstrap["company_id"],
            "candidate_id": cid,
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    res = await client.get(f"/api/v1/workforce/employees/{emp_id}/documents", headers=hr_officer_headers)
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_recruiter_delete_employee(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={"display_name": "To delete", "status": "onboarding", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]
    del_res = await client.delete(f"/api/v1/workforce/employees/{emp_id}", headers=hr_officer_headers)
    assert del_res.status_code == 204, del_res.text
    gone = await client.get(f"/api/v1/workforce/employees/{emp_id}", headers=hr_officer_headers)
    assert gone.status_code == 404, gone.text


@pytest.mark.asyncio
async def test_recruiter_handoff_from_candidate(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    """Uses isolated candidate (manager = recruiter) — shared DB may have legacy candidates that fail ACL."""
    cid = candidate_id
    h = {**recruiter_headers, "Content-Type": "application/json"}
    resp = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{cid}",
        headers=h,
        json={},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("id")
    assert str(data.get("candidate_id") or "") == str(cid)
    snap = data.get("candidate_snapshot") or {}
    assert isinstance(snap.get("personal_data"), dict)
    assert isinstance(snap.get("contacts"), dict)
    assert isinstance(snap.get("extra"), dict)
    assert isinstance(snap.get("vacancy_context"), dict)
    assert isinstance(snap.get("document_field_values"), dict)


@pytest.mark.asyncio
async def test_viewer_workforce_list_forbidden(client: AsyncClient, viewer_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/employees", headers=viewer_headers)
    assert resp.status_code == 403, resp.text
