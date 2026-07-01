"""HR Dashboard Summary API (MVP)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from backend.tests.api.test_hr_documents_queue import (
    _ensure_tenant_link_internal_hr,
    _internal_hr_handoff_accepted,
)
from backend.tests.conftest import _init_data
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


@pytest.mark.anyio
async def test_hr_dashboard_recruiter_forbidden(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
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
    for path in (
        "/api/v1/hr/dashboard/summary",
        "/api/v1/hr/dashboard/high-risk",
        "/api/v1/hr/dashboard/workload",
        "/api/v1/hr/dashboard/compliance",
    ):
        r = await client.get(path, headers=recruiter_headers)
        assert r.status_code == 403, r.text


@pytest.mark.anyio
async def test_hr_dashboard_summary_counters(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Dash", "last_name": f"S{tag}", "company_id": company_id},
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)
    await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    hid = ho.json()["id"]

    s1 = await client.get("/api/v1/hr/dashboard/summary", headers=hr_officer_headers)
    assert s1.status_code == 200, s1.text
    b1 = s1.json()
    assert b1.get("schema_version") == 1
    assert "risk_summary" in b1
    assert b1["risk_summary"]["total"] >= 0
    c1 = b1["counts"]
    assert c1["handoffs_pending"] >= 1
    assert c1["hr_tasks_open"] >= 1

    await client.post(f"/api/v1/handoffs/{hid}/accept", headers=hr_officer_headers)

    lst = await client.get(
        "/api/v1/documents/",
        headers=manager_headers,
        params={"candidate_id": candidate_id},
    )
    assert lst.status_code == 200, lst.text
    code95_id = next(x["id"] for x in lst.json() if str(x.get("type") or "") == "code95")
    await client.patch(
        f"/api/v1/documents/{code95_id}",
        headers=manager_headers,
        json={"status": "rejected"},
    )
    exp = (date.today() + timedelta(days=5)).isoformat()
    wp = await client.post(
        "/api/v1/documents/",
        headers=manager_headers,
        json={
            "candidate_id": candidate_id,
            "type": "work_permit",
            "status": "approved",
            "expires_at": exp,
        },
    )
    assert wp.status_code == 200, wp.text

    s2 = await client.get("/api/v1/hr/dashboard/summary", headers=hr_officer_headers)
    assert s2.status_code == 200, s2.text
    b2 = s2.json()
    assert b2["schema_version"] == 1
    c2 = b2["counts"]
    assert c2["handoffs_accepted"] >= 1
    assert c2["documents_missing"] >= 1
    assert c2["documents_high_risk_expiring"] >= 1
    rs = b2["risk_summary"]
    assert rs["total"] >= 1
    assert rs["counts_by_code"].get("missing_high_risk_document", 0) >= 1
    assert rs["counts_by_code"].get("document_expiring_soon", 0) >= 1


@pytest.mark.anyio
async def test_hr_dashboard_high_risk_item(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    candidate_id, hid, _ = await _internal_hr_handoff_accepted(
        client,
        manager_headers=manager_headers,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    exp = (date.today() + timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/documents/",
        headers=manager_headers,
        json={
            "candidate_id": candidate_id,
            "type": "work_permit",
            "status": "approved",
            "expires_at": exp,
        },
    )
    r = await client.get(
        "/api/v1/hr/dashboard/high-risk",
        headers=hr_officer_headers,
        params={"horizon_days": 30, "handoff_id": hid},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schema_version"] == 2
    rows = [x for x in body["items"] if x.get("document_type") == "work_permit"]
    assert rows
    assert rows[0]["risk_code"] == "document_expiring_soon"
    assert rows[0]["severity"] in ("low", "medium", "high", "critical")
    assert rows[0]["expires_at"] == exp


@pytest.mark.anyio
async def test_hr_dashboard_workload_groups_tasks(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Dash", "last_name": f"W{tag}", "company_id": company_id},
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)
    await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    hid = ho.json()["id"]

    w = await client.get(
        "/api/v1/hr/dashboard/workload",
        headers=hr_officer_headers,
        params={"assignee_scope": "team"},
    )
    assert w.status_code == 200, w.text
    body = w.json()
    assert body["schema_version"] == 1
    groups = body["groups"]
    assert groups
    all_types: set[str] = set()
    for g in groups:
        assert "assignee_user_id" in g
        assert g["open_task_count"] >= 0
        for t in g.get("tasks") or []:
            all_types.add(str(t.get("type") or ""))
    assert "internal_hr_handoff_pending" in all_types

    acc2 = await client.post(f"/api/v1/handoffs/{hid}/accept", headers=hr_officer_headers)
    assert acc2.status_code == 200, acc2.text

    w2 = await client.get(
        "/api/v1/hr/dashboard/workload",
        headers=hr_officer_headers,
        params={"assignee_scope": "team"},
    )
    assert w2.status_code == 200, w2.text
    types2: set[str] = set()
    for g in w2.json()["groups"]:
        for t in g.get("tasks") or []:
            types2.add(str(t.get("type") or ""))
    assert "handoff_hr_checklist" in types2 or "internal_hr_handoff_pending" in types2


@pytest.mark.anyio
async def test_hr_dashboard_compliance_grouping(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    candidate_id, hid, _ = await _internal_hr_handoff_accepted(
        client,
        manager_headers=manager_headers,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    lst = await client.get(
        "/api/v1/documents/",
        headers=manager_headers,
        params={"candidate_id": candidate_id},
    )
    code95_id = next(x["id"] for x in lst.json() if str(x.get("type") or "") == "code95")
    await client.patch(
        f"/api/v1/documents/{code95_id}",
        headers=manager_headers,
        json={"status": "rejected"},
    )

    r = await client.get(
        "/api/v1/hr/dashboard/compliance",
        headers=hr_officer_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schema_version"] == 1
    assert body["total"] >= 1
    dt = {x["document_type"]: x for x in body["by_document_type"]}
    assert "code95" in dt
    assert dt["code95"]["count"] >= 1
    cand_rows = [x for x in body["by_candidate"] if x.get("handoff_id") == hid]
    assert cand_rows
    assert "code95" in cand_rows[0]["document_types"]
