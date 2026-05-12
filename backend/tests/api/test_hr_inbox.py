"""HR Inbox API (internal-HR lane)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.tests.conftest import _init_data
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


async def _ensure_tenant_link_internal_hr(
    client: AsyncClient,
    *,
    manager_headers: dict[str, str],
    tenant_id: str,
    company_id: str,
) -> None:
    lst = await client.get(
        f"/api/v1/tenants/{tenant_id}/links",
        headers=manager_headers,
    )
    assert lst.status_code == 200, lst.text
    for row in lst.json():
        if str(row.get("client_company_id") or "") == str(company_id):
            link_id = row["id"]
            patch = await client.patch(
                f"/api/v1/tenants/{tenant_id}/links/{link_id}",
                headers=manager_headers,
                json={
                    "handoff_enabled": True,
                    "handoff_to_client": True,
                    "handoff_to_internal_hr": True,
                },
            )
            assert patch.status_code == 200, patch.text
            return
    create = await client.post(
        f"/api/v1/tenants/{tenant_id}/links",
        headers=manager_headers,
        json={
            "client_company_id": company_id,
            "handoff_enabled": True,
            "handoff_to_client": True,
            "handoff_to_internal_hr": True,
        },
    )
    assert create.status_code == 201, create.text


@pytest.mark.anyio
async def test_hr_inbox_pending_tasks_accepted_and_recruiter_forbidden(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]

    mod = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    assert mod.status_code == 200, mod.text

    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    denied = await client.get(
        "/api/v1/hr/handoffs/pending",
        headers=recruiter_headers,
    )
    assert denied.status_code == 403, denied.text

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Inbox", "last_name": f"T{tag}", "company_id": company_id},
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)
    patch_resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    hid = ho.json()["id"]

    pending = await client.get(
        "/api/v1/hr/handoffs/pending",
        headers=hr_officer_headers,
    )
    assert pending.status_code == 200, pending.text
    body = pending.json()
    assert body["total"] >= 1
    ids = {item["handoff"]["id"] for item in body["items"]}
    assert hid in ids
    snap_row = next(item for item in body["items"] if item["handoff"]["id"] == hid)
    assert snap_row.get("snapshot") is not None
    assert snap_row["snapshot"].get("handoff", {}).get("handoff_id") == hid

    tasks = await client.get(
        "/api/v1/hr/tasks",
        headers=hr_officer_headers,
    )
    assert tasks.status_code == 200, tasks.text
    ttypes = {item.get("type") for item in tasks.json().get("items", [])}
    assert "internal_hr_handoff_pending" in ttypes

    acc = await client.post(
        f"/api/v1/handoffs/{hid}/accept",
        headers=hr_officer_headers,
    )
    assert acc.status_code == 200, acc.text

    accepted = await client.get(
        "/api/v1/hr/handoffs/accepted",
        headers=hr_officer_headers,
    )
    assert accepted.status_code == 200, accepted.text
    ab = accepted.json()
    assert ab["total"] >= 1
    row = next(x for x in ab["items"] if x["handoff"]["id"] == hid)
    assert row.get("workforce_employee_id") is not None
