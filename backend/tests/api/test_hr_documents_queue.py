"""HR documents queues (missing / expiring)."""

from __future__ import annotations

import copy
import uuid
from datetime import date, timedelta

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.db.session import async_session_maker
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.tests.conftest import _init_data, _set_tenant
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


async def _internal_hr_handoff_accepted(
    client: AsyncClient,
    *,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
    tenant_id: str,
    company_id: str,
) -> tuple[str, str, str]:
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "DocQ", "last_name": f"T{tag}", "company_id": company_id},
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
    acc = await client.post(
        f"/api/v1/handoffs/{hid}/accept",
        headers=hr_officer_headers,
    )
    assert acc.status_code == 200, acc.text
    return candidate_id, hid, tag


@pytest.mark.anyio
async def test_hr_documents_missing_after_accept_and_recruiter_forbidden(
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

    denied = await client.get(
        "/api/v1/hr/documents/missing",
        headers=recruiter_headers,
    )
    assert denied.status_code == 403, denied.text

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
    assert lst.status_code == 200, lst.text
    code95_id = None
    for item in lst.json():
        if str(item.get("type") or item.get("doc_type") or "") == "code95":
            code95_id = item["id"]
            break
    assert code95_id is not None
    ch = await client.patch(
        f"/api/v1/documents/{code95_id}",
        headers=manager_headers,
        json={"status": "rejected"},
    )
    assert ch.status_code == 200, ch.text

    miss = await client.get(
        "/api/v1/hr/documents/missing",
        headers=hr_officer_headers,
        params={"handoff_id": hid, "document_type": "code95"},
    )
    assert miss.status_code == 200, miss.text
    body = miss.json()
    assert body["total"] >= 1
    row = body["items"][0]
    assert row["handoff_id"] == hid
    assert row["document_type"] == "code95"
    assert row["current_status"] == "rejected"


@pytest.mark.anyio
async def test_hr_documents_expiring_high_risk_live_horizon(
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
    wp = await client.post(
        "/api/v1/documents/",
        headers=manager_headers,
        json={
            "candidate_id": candidate_id,
            "type": "work_permit",
            "status": "approved",
            "expires_at": exp,
            "extra": {"title": "wp-exp"},
        },
    )
    assert wp.status_code == 200, wp.text
    wp_id = wp.json()["id"]

    ex = await client.get(
        "/api/v1/hr/documents/expiring",
        headers=hr_officer_headers,
        params={
            "horizon_days": 30,
            "status": "expiring",
            "risk": "high",
            "document_type": "work_permit",
            "handoff_id": hid,
        },
    )
    assert ex.status_code == 200, ex.text
    rows = [r for r in ex.json()["items"] if r.get("document_type") == "work_permit"]
    assert rows, ex.text
    assert rows[0]["expires_at"] == exp

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        snap = (
            await session.execute(
                sa.select(CandidateHandoffSnapshot).where(
                    CandidateHandoffSnapshot.handoff_id == hid
                )
            )
        ).scalar_one()
        pl = copy.deepcopy(dict(snap.payload))
        for d in pl.get("documents") or []:
            if str(d.get("type") or "") == "work_permit":
                d["expires_at"] = "2099-12-31"
                d["status"] = "approved"
        snap.payload = pl
        await session.commit()

    ex2 = await client.get(
        "/api/v1/hr/documents/expiring",
        headers=hr_officer_headers,
        params={
            "horizon_days": 30,
            "status": "expiring",
            "risk": "high",
            "document_type": "work_permit",
            "handoff_id": hid,
        },
    )
    assert ex2.status_code == 200, ex2.text
    row2 = next(r for r in ex2.json()["items"] if r.get("document_type") == "work_permit")
    assert row2["expires_at"] == exp
    assert row2["expires_at"] != "2099-12-31"

    await client.delete(f"/api/v1/documents/{wp_id}", headers=manager_headers)


@pytest.mark.anyio
async def test_hr_documents_missing_snapshot_context_not_live_valid(
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
    code95_id = next(
        x["id"] for x in lst.json() if str(x.get("type") or "") == "code95"
    )
    await client.patch(
        f"/api/v1/documents/{code95_id}",
        headers=manager_headers,
        json={"status": "rejected"},
    )

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        snap = (
            await session.execute(
                sa.select(CandidateHandoffSnapshot).where(
                    CandidateHandoffSnapshot.handoff_id == hid
                )
            )
        ).scalar_one()
        pl = copy.deepcopy(dict(snap.payload))
        found = False
        for d in pl.get("documents") or []:
            if str(d.get("type") or "") == "code95":
                d["status"] = "approved"
                found = True
                break
        if not found:
            pl.setdefault("documents", []).append(
                {"type": "code95", "status": "approved", "expires_at": None, "verified_at": None}
            )
        snap.payload = pl
        await session.commit()

    miss = await client.get(
        "/api/v1/hr/documents/missing",
        headers=hr_officer_headers,
        params={"handoff_id": hid, "document_type": "code95"},
    )
    assert miss.status_code == 200, miss.text
    row = miss.json()["items"][0]
    assert row["snapshot_status"] == "approved"
    assert row["current_status"] == "rejected"
