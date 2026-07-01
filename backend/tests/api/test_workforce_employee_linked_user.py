"""Workforce employee linked_user_id + org units projection (P1 HR).

Covers DB migration ``202604302490_workforce_linked_user`` (column ``linked_user_id`` on
``workforce_employees``). That revision is linear after the Fleet chain — not a parallel merge;
API tests here do not replace migrations.
"""

from __future__ import annotations

import uuid
from typing import Dict

import pytest
from httpx import AsyncClient

from backend.tests.conftest import _init_data


@pytest.mark.anyio
async def test_workforce_linked_user_shows_org_units_and_duplicate_forbidden(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
) -> None:
    data = await _init_data()
    viewer_id = data["viewer_id"]
    h_hr = {**hr_officer_headers, "Content-Type": "application/json"}
    h_mgr = {**manager_headers, "Content-Type": "application/json"}

    emp = await client.post(
        "/api/v1/workforce/employees",
        headers=h_hr,
        json={"display_name": "Linked HR employee", "status": "onboarding"},
    )
    assert emp.status_code == 201, emp.text
    emp_id = emp.json()["id"]

    code = f"L-{uuid.uuid4().hex[:6]}"
    org = await client.post(
        "/api/v1/admin/org-units",
        headers=h_mgr,
        json={"name": "HR-Link-Dept", "unit_type": "department", "code": code},
    )
    assert org.status_code == 201, org.text
    unit_id = org.json()["id"]

    patch_u = await client.patch(
        f"/api/v1/admin/users/{viewer_id}/org-units",
        headers=h_mgr,
        json={"org_unit_ids": [unit_id]},
    )
    assert patch_u.status_code == 200, patch_u.text

    patch_e = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}",
        headers=h_hr,
        json={"linked_user_id": viewer_id},
    )
    assert patch_e.status_code == 200, patch_e.text
    body = patch_e.json()
    assert body.get("linked_user_id") == viewer_id
    units = body.get("linked_user_org_units") or []
    assert any(u.get("org_unit_id") == unit_id for u in units)

    opts = await client.get("/api/v1/workforce/employees/link-user-options", headers=h_hr)
    assert opts.status_code == 200, opts.text
    assert any(o.get("user_id") == viewer_id for o in opts.json())

    emp2 = await client.post(
        "/api/v1/workforce/employees",
        headers=h_hr,
        json={"display_name": "Second employee", "status": "onboarding"},
    )
    assert emp2.status_code == 201, emp2.text
    dup = await client.patch(
        f"/api/v1/workforce/employees/{emp2.json()['id']}",
        headers=h_hr,
        json={"linked_user_id": viewer_id},
    )
    assert dup.status_code == 409, dup.text

    await client.patch(f"/api/v1/workforce/employees/{emp_id}", headers=h_hr, json={"linked_user_id": None})
    await client.patch(f"/api/v1/admin/users/{viewer_id}/org-units", headers=h_mgr, json={"org_unit_ids": []})
    await client.delete(f"/api/v1/admin/org-units/{unit_id}", headers=h_mgr)
