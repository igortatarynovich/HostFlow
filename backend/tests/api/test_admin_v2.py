from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.core.security import hash_password
from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.user import Role as UserRole
from backend.app.models.user import User
from backend.tests.conftest import _build_token, _init_data

ADMIN_USERS_PREFIX = "/api/v1/admin/users"
ADMIN_COMPANIES_PREFIX = "/api/v1/admin/companies"


def _headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "Content-Type": "application/json",
    }


async def _auth_headers(user_id: str, email: str, role: str, tenant_id: str) -> dict[str, str]:
    token = _build_token(user_id, email, role, tenant_id)
    return _headers(token, tenant_id)


@pytest.mark.anyio
async def test_invite_accept_assigns_role_and_acl(client: AsyncClient) -> None:
    data = await _init_data()
    admin_headers = await _auth_headers(
        data["admin_id"], data["admin_email"], "administrator", data["tenant_id"]
    )

    invite_payload = {
        "email": f"recruiter+{uuid.uuid4().hex[:6]}@hostflow.dev",
        "role": "recruiter",
        "supervisor_id": data["supervisor_id"],
        "company_ids": [data["company_id"]],
        "expires_in_hours": 24,
    }
    invite_resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/invite", headers=admin_headers, json=invite_payload
    )
    assert invite_resp.status_code == 201, invite_resp.text
    invite_data = invite_resp.json()
    assert invite_data["role"] == "recruiter"
    token = invite_data["token"]

    new_password = "Recruiter123!"
    accept_resp = await client.post(
        "/api/v1/auth/invite/accept",
        json={
            "token": token,
            "password": new_password,
            "full_name": "Recruiter Test",
            "short_id": "REC999",
        },
    )
    assert accept_resp.status_code == 200, accept_resp.text
    accepted = accept_resp.json()
    assert accepted["role"] == "recruiter"
    assert accepted["supervisor_id"] == data["supervisor_id"]
    assert accepted["status"] == "active"
    company_ids = {entry["company_id"] for entry in accepted.get("companies", [])}
    assert data["company_id"] in company_ids

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": invite_payload["email"], "password": new_password},
    )
    assert login_resp.status_code == 200, login_resp.text
    assert login_resp.json()["user"]["role"] == "recruiter"


@pytest.mark.anyio
async def test_supervisor_company_access_scope(client: AsyncClient) -> None:
    data = await _init_data()
    supervisor_headers = await _auth_headers(
        data["supervisor_id"], data["supervisor_email"], "supervisor", data["tenant_id"]
    )

    # Supervisor can grant access to their recruiter
    grant_resp = await client.post(
        f"{ADMIN_COMPANIES_PREFIX}/{data['company_id']}/access",
        headers=supervisor_headers,
        json={"user_id": data["recruiter_id"], "can_edit": True},
    )
    assert grant_resp.status_code == 200, grant_resp.text
    grant_data = grant_resp.json()
    assert grant_data["user_id"] == data["recruiter_id"]
    assert grant_data["can_edit"] is True

    list_resp = await client.get(
        f"{ADMIN_COMPANIES_PREFIX}/{data['company_id']}/access",
        headers=supervisor_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    entries = list_resp.json()
    assert any(entry["user_id"] == data["recruiter_id"] for entry in entries)
    # Supervisors should not see unrelated users in the ACL listing
    assert all(
        entry["user_id"] in {data["recruiter_id"], data["supervisor_id"]}
        for entry in entries
    )

    # Create recruiter belonging to another supervisor
    async with async_session_maker() as session:
        other_supervisor = User(
            id=str(uuid.uuid4()),
            email=f"sup+{uuid.uuid4().hex[:5]}@hostflow.dev",
            password_hash=hash_password("Sup12345!"),
            role=UserRole.supervisor,
            tenant_id=data["tenant_id"],
            is_active=True,
        )
        session.add(other_supervisor)

        other_recruiter = User(
            id=str(uuid.uuid4()),
            email=f"rec+{uuid.uuid4().hex[:5]}@hostflow.dev",
            password_hash=hash_password("Rec12345!"),
            role=UserRole.recruiter,
            supervisor_id=other_supervisor.id,
            tenant_id=data["tenant_id"],
            is_active=True,
        )
        session.add(other_recruiter)
        await session.flush()
        await session.execute(
            sa.text(
                """
                INSERT INTO user_memberships (id, user_id, tenant_id, role)
                VALUES (:id, :user_id, :tenant_id, :role)
                ON CONFLICT(user_id, tenant_id) DO UPDATE SET role = excluded.role
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": other_supervisor.id,
                "tenant_id": data["tenant_id"],
                "role": "supervisor",
            },
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO user_memberships (id, user_id, tenant_id, role)
                VALUES (:id, :user_id, :tenant_id, :role)
                ON CONFLICT(user_id, tenant_id) DO UPDATE SET role = excluded.role
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": other_recruiter.id,
                "tenant_id": data["tenant_id"],
                "role": "recruiter",
            },
        )
        other_recruiter_id = other_recruiter.id
        await session.commit()

    # Supervisor should be forbidden to manage foreign recruiters
    foreign_resp = await client.post(
        f"{ADMIN_COMPANIES_PREFIX}/{data['company_id']}/access",
        headers=supervisor_headers,
        json={"user_id": other_recruiter_id, "can_edit": False},
    )
    assert foreign_resp.status_code == 403


@pytest.mark.anyio
async def test_candidate_delete_workflow(client: AsyncClient) -> None:
    data = await _init_data()
    recruiter_headers = await _auth_headers(
        data["recruiter_id"], data["recruiter_email"], "recruiter", data["tenant_id"]
    )
    supervisor_headers = await _auth_headers(
        data["supervisor_id"], data["supervisor_email"], "supervisor", data["tenant_id"]
    )

    delete_req_resp = await client.post(
        f"/api/v1/candidates/{data['candidate_id']}/delete-request",
        headers=recruiter_headers,
        json={"reason": "Outdated profile"},
    )
    assert delete_req_resp.status_code == 201, delete_req_resp.text
    delete_req = delete_req_resp.json()
    assert delete_req["status"] == "pending"
    request_id = delete_req["id"]
    assert delete_req["candidate"]["id"] == data["candidate_id"]
    assert delete_req["requested_by_user"]["id"] == data["recruiter_id"]
    assert delete_req["supervisor_user"]["id"] == data["supervisor_id"]

    direct_delete_resp = await client.delete(
        f"/api/v1/candidates/{data['candidate_id']}",
        headers=recruiter_headers,
    )
    assert direct_delete_resp.status_code == 403

    queue_resp = await client.get(
        "/api/v1/delete-requests",
        headers=supervisor_headers,
    )
    assert queue_resp.status_code == 200, queue_resp.text
    queue = queue_resp.json()
    assert any(item["id"] == request_id for item in queue)
    for item in queue:
        assert "candidate" in item
        assert "requested_by_user" in item

    approve_resp = await client.post(
        f"/api/v1/delete-requests/{request_id}/approve",
        headers=supervisor_headers,
        json={"decision": "approve", "comment": "Confirmed"},
    )
    assert approve_resp.status_code == 200, approve_resp.text
    approved = approve_resp.json()
    assert approved["status"] == "approved"
    assert approved["resolved_by"] == data["supervisor_id"]

    async with async_session_maker() as session:
        candidate = await session.get(Candidate, data["candidate_id"])
        assert candidate is not None
        assert candidate.deleted_at is not None
