"""Handoff snapshot: created at handoff create, immutable, ACL."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.core.security import hash_password
from backend.app.db.session import async_session_maker
from backend.app.models.user import Role as UserRole, User
from backend.tests.conftest import _build_token, _init_data, _set_tenant
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
async def test_handoff_snapshot_immutable_after_candidate_and_doc_changes(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "Snap",
            "last_name": f"T{tag}",
            "company_id": company_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    patch_resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={
            "stage": "ready_for_handoff",
            "note": "recruitment-visible note",
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text

    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    hid = ho.json()["id"]

    snap1 = await client.get(
        f"/api/v1/handoffs/{hid}/snapshot",
        headers=recruiter_headers,
    )
    assert snap1.status_code == 200, snap1.text
    body1 = snap1.json()
    assert body1["handoff"]["handoff_id"] == hid
    assert body1["candidate"]["name"]["first_name"] == "Snap"
    assert body1["notes_summary"] == "recruitment-visible note"

    hr_snap = await client.get(
        f"/api/v1/handoffs/{hid}/snapshot",
        headers=hr_officer_headers,
    )
    assert hr_snap.status_code == 200, hr_snap.text
    assert hr_snap.json() == body1

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        await session.execute(
            sa.text(
                "UPDATE candidates SET first_name = :fn, note = :note WHERE id = :id"
            ),
            {"fn": "Changed", "note": "mutated after snapshot", "id": candidate_id},
        )
        doc_row = await session.execute(
            sa.text(
                "SELECT id FROM documents WHERE candidate_id = :c AND deleted_at IS NULL LIMIT 1"
            ),
            {"c": candidate_id},
        )
        doc_id = doc_row.scalar_one()
        await session.execute(
            sa.text("UPDATE documents SET status = :st WHERE id = :id"),
            {"st": "in_progress", "id": doc_id},
        )
        await session.commit()

    ch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={
            "first_name": "Changed",
            "note": "new note after snapshot",
        },
    )
    assert ch.status_code == 403, ch.text

    snap2 = await client.get(
        f"/api/v1/handoffs/{hid}/snapshot",
        headers=recruiter_headers,
    )
    assert snap2.status_code == 200, snap2.text
    assert snap2.json() == body1


@pytest.mark.anyio
async def test_hr_officer_cannot_read_client_portal_handoff_snapshot(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Cli", "last_name": f"T{tag}", "company_id": company_id},
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
        json={"client_company_id": company_id},
    )
    assert ho.status_code == 201, ho.text
    hid = ho.json()["id"]
    assert ho.json().get("destination") == "client_portal"

    denied = await client.get(
        f"/api/v1/handoffs/{hid}/snapshot",
        headers=hr_officer_headers,
    )
    assert denied.status_code == 403, denied.text

    ok = await client.get(
        f"/api/v1/handoffs/{hid}/snapshot",
        headers=recruiter_headers,
    )
    assert ok.status_code == 200, ok.text


@pytest.mark.anyio
async def test_client_processor_can_read_own_company_handoff_snapshot(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    proc_id = str(uuid.uuid4())
    proc_email = f"proc_snap_{uuid.uuid4().hex[:8]}@example.com"
    async with async_session_maker() as session:
        session.add(
            User(
                id=proc_id,
                email=proc_email,
                password_hash=hash_password("Test123!"),
                role=UserRole.employee,
                short_id=f"P{uuid.uuid4().hex[:6]}",
                full_name="Snapshot Client Processor",
                tenant_id=tenant_id,
                is_active=True,
                preferences={},
            )
        )
        await session.commit()

    import sqlalchemy as sa

    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                INSERT INTO user_memberships (id, user_id, tenant_id, role)
                VALUES (:id, :user_id, :tenant_id, :role)
                ON CONFLICT(user_id, tenant_id)
                DO UPDATE SET role = excluded.role
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": proc_id,
                "tenant_id": tenant_id,
                "role": "client_processor",
            },
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO user_company_access (id, tenant_id, user_id, company_id, can_edit)
                VALUES (:id, :tenant_id, :user_id, :company_id, TRUE)
                ON CONFLICT (tenant_id, user_id, company_id) DO NOTHING
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "user_id": proc_id,
                "company_id": company_id,
            },
        )
        await session.commit()

    proc_headers = {
        "Authorization": f"Bearer {_build_token(proc_id, proc_email, 'client_processor', tenant_id)}",
        "X-Tenant-Id": tenant_id,
    }

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Proc", "last_name": f"T{tag}", "company_id": company_id},
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
        json={"client_company_id": company_id},
    )
    assert ho.status_code == 201, ho.text
    hid = ho.json()["id"]

    snap = await client.get(
        f"/api/v1/handoffs/{hid}/snapshot",
        headers=proc_headers,
    )
    assert snap.status_code == 200, snap.text
    assert snap.json()["handoff"]["handoff_id"] == hid
