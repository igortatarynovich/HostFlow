import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.core.security import verify_password
from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.db.session import async_session_maker
from backend.app.models.session import AuthRefreshToken
from backend.app.models.tenant import user_memberships
from backend.app.models.user import User
from backend.tests.conftest import _init_data

ADMIN_USERS_PREFIX = "/api/v1/admin/users"


def _make_token(user_id: str, email: str, role: str, tenant_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=2)).timestamp()),
    }
    return encode_jwt(payload)


async def _headers_for(role: str) -> Dict[str, str]:
    data = await _init_data()
    token = _make_token(data["admin_id"], data["admin_email"], role, data["tenant_id"])
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": data["tenant_id"],
        "Content-Type": "application/json",
    }


@pytest.mark.anyio
async def test_owner_invite_role_change_activation_flow(
    client: AsyncClient, viewer_headers: Dict[str, str]
) -> None:
    owner_headers = await _headers_for("administrator")
    data = await _init_data()

    # List users
    resp = await client.get(ADMIN_USERS_PREFIX, headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)

    # Create invite
    new_email = f"newuser+{uuid.uuid4().hex[:6]}@hostflow.dev"
    invite_payload = {
        "email": new_email,
        "role": "recruiter",
        "supervisor_id": data["admin_id"],
    }
    invite_resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/invite", headers=owner_headers, json=invite_payload
    )
    assert invite_resp.status_code == 201, invite_resp.text
    invite_data = invite_resp.json()
    assert invite_data["email"] == new_email
    assert invite_data["role"] == "recruiter"
    assert "token" in invite_data and invite_data["token"]

    # Change viewer role to manager
    role_resp = await client.patch(
        f"{ADMIN_USERS_PREFIX}/{data['viewer_id']}/role",
        headers=owner_headers,
        json={"role": "supervisor"},
    )
    assert role_resp.status_code == 200, role_resp.text
    role_body = role_resp.json()
    assert role_body["role"] == "supervisor"

    # Deactivate viewer
    deactivate_resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/{data['viewer_id']}/deactivate",
        headers=owner_headers,
    )
    assert deactivate_resp.status_code == 200, deactivate_resp.text
    deactivate_payload = deactivate_resp.json()
    assert deactivate_payload["status"] == "inactive"
    assert deactivate_payload["is_active"] is False

    # Activate viewer
    activate_resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/{data['viewer_id']}/activate",
        headers=owner_headers,
    )
    assert activate_resp.status_code == 200, activate_resp.text
    activate_payload = activate_resp.json()
    assert activate_payload["status"] == "active"
    assert activate_payload["is_active"] is True

    # Prepare refresh token row and revoke
    async with async_session_maker() as session:
        token = AuthRefreshToken(
            id=str(uuid.uuid4()),
            user_id=data["viewer_id"],
            tenant_id=data["tenant_id"],
            token_hash=uuid.uuid4().hex,
        )
        session.add(token)
        await session.commit()

    revoke_resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/{data['viewer_id']}/sessions/revoke",
        headers=owner_headers,
    )
    assert revoke_resp.status_code == 200, revoke_resp.text
    revoke_payload = revoke_resp.json()
    assert revoke_payload["revoked"] >= 1

    # Audit trail should contain entries
    audit_resp = await client.get(
        f"{ADMIN_USERS_PREFIX}/{data['viewer_id']}/audit",
        headers=owner_headers,
    )
    assert audit_resp.status_code == 200, audit_resp.text
    audit_entries: List[Dict[str, str]] = audit_resp.json()
    actions = [entry["action"] for entry in audit_entries]
    assert "user.role_changed" in actions
    assert "user.deactivated" in actions
    assert "user.activated" in actions
    assert "user.refresh_revoked" in actions


@pytest.mark.anyio
async def test_manager_cannot_access_admin_users(client: AsyncClient) -> None:
    manager_headers = await _headers_for("supervisor")
    resp = await client.get(ADMIN_USERS_PREFIX, headers=manager_headers)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_viewer_cannot_access_admin_users(
    client: AsyncClient, viewer_headers: Dict[str, str]
) -> None:
    resp = await client.get(ADMIN_USERS_PREFIX, headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_deactivate_self_blocked(client: AsyncClient) -> None:
    owner_headers = await _headers_for("administrator")
    data = await _init_data()
    resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/{data['admin_id']}/deactivate", headers=owner_headers
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_owner_can_create_user_without_password(client: AsyncClient) -> None:
    owner_headers = await _headers_for("administrator")
    new_email = f"create+{uuid.uuid4().hex[:6]}@hostflow.dev"
    payload = {
        "email": new_email,
        "role": "supervisor",
        "full_name": "QA Manager",
        "short_id": "QA001",
    }

    resp = await client.post(ADMIN_USERS_PREFIX, headers=owner_headers, json=payload)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["email"] == new_email
    assert created["role"] == "supervisor"
    assert created["status"] == "active"
    assert created.get("temporary_password")

    # Listing should contain the new user (temporary password not included)
    list_resp = await client.get(ADMIN_USERS_PREFIX, headers=owner_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    emails = [item["email"] for item in items]
    assert new_email in emails


@pytest.mark.anyio
async def test_owner_can_reset_change_and_delete_user(client: AsyncClient) -> None:
    owner_headers = await _headers_for("administrator")
    new_email = f"reset+{uuid.uuid4().hex[:6]}@hostflow.dev"
    create_resp = await client.post(
        ADMIN_USERS_PREFIX,
        headers=owner_headers,
        json={
            "email": new_email,
            "role": "viewer",
            "full_name": "Temp User",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    user_id = create_resp.json()["user_id"]

    async with async_session_maker() as session:
        user_before = await session.scalar(sa.select(User).where(User.id == user_id))
        assert user_before is not None
        original_hash = user_before.password_hash

    reset_resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/{user_id}/password/reset",
        headers=owner_headers,
    )
    assert reset_resp.status_code == 200, reset_resp.text
    reset_data = reset_resp.json()
    assert reset_data["temporary_password"]
    assert reset_data["revoked_sessions"] >= 0

    async with async_session_maker() as session:
        user_after_reset = await session.scalar(sa.select(User).where(User.id == user_id))
        assert user_after_reset is not None
        assert user_after_reset.password_hash != original_hash
        assert verify_password(reset_data["temporary_password"], user_after_reset.password_hash)

    change_resp = await client.post(
        f"{ADMIN_USERS_PREFIX}/{user_id}/password",
        headers=owner_headers,
        json={"new_password": "NewStrongPass1!", "revoke_sessions": True},
    )
    assert change_resp.status_code == 200, change_resp.text
    change_data = change_resp.json()
    assert change_data["revoked"] >= 0

    async with async_session_maker() as session:
        user_after_change = await session.scalar(sa.select(User).where(User.id == user_id))
        assert user_after_change is not None
        assert verify_password("NewStrongPass1!", user_after_change.password_hash)

    delete_resp = await client.delete(
        f"{ADMIN_USERS_PREFIX}/{user_id}",
        headers=owner_headers,
    )
    assert delete_resp.status_code == 200, delete_resp.text
    delete_data = delete_resp.json()
    assert delete_data["deleted"] is True
    assert delete_data["revoked_sessions"] >= 0

    async with async_session_maker() as session:
        deleted_user = await session.scalar(sa.select(User).where(User.id == user_id))
        assert deleted_user is not None
        assert deleted_user.is_active is False
        assert deleted_user.deleted_at is not None
        membership_row = await session.execute(
            sa.select(user_memberships.c.id).where(user_memberships.c.user_id == user_id)
        )
        assert membership_row.scalar_one_or_none() is None
