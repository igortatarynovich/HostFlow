from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.db.session import async_session_maker
from backend.app.models.user import User
from backend.tests.conftest import _init_data

PLATFORM_ENDPOINT = "/api/v1/platform/tenants"
TEAM_ENDPOINT = "/api/v1/settings/team"
ADMIN_USERS_ENDPOINT = "/api/v1/admin/users"
PLATFORM_MODULES = f"{PLATFORM_ENDPOINT}/{{tenant_id}}/modules"
PLATFORM_SEAT_REQUESTS = f"{PLATFORM_ENDPOINT}/{{tenant_id}}/seat-requests"


def _make_token(user_id: str, email: str, role: str, tenant_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return encode_jwt(payload)


async def _headers(role: str = "superadmin", include_tenant: bool = False) -> Dict[str, str]:
    data = await _init_data()
    token = _make_token(data["admin_id"], data["admin_email"], role, data["tenant_id"])
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if include_tenant:
        headers["X-Tenant-Id"] = data["tenant_id"]
    return headers


@pytest.mark.anyio
async def test_platform_list_requires_superadmin(client: AsyncClient) -> None:
    headers = await _headers()
    resp = await client.get(PLATFORM_ENDPOINT, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)


@pytest.mark.anyio
async def test_platform_list_forbidden_for_admin(client: AsyncClient) -> None:
    headers = await _headers(role="administrator")
    resp = await client.get(PLATFORM_ENDPOINT, headers=headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.anyio
async def test_team_overview_includes_members_and_usage(client: AsyncClient) -> None:
    headers = await _headers(role="administrator", include_tenant=True)
    resp = await client.get(TEAM_ENDPOINT, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "members" in body and isinstance(body["members"], list)
    assert "usage" in body and "recruiter_count" in body["usage"]
    assert "tenant" in body and body["tenant"]["name"]


@pytest.mark.anyio
async def test_platform_patch_updates_workspace_label(client: AsyncClient) -> None:
    headers = await _headers()
    data = await _init_data()
    tenant_id = data["tenant_id"]
    resp = await client.patch(
        f"{PLATFORM_ENDPOINT}/{tenant_id}",
        headers=headers,
        json={"workspace_label": "Test Client Group"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["workspace_label"] == "Test Client Group"


@pytest.mark.anyio
async def test_platform_logo_upload_updates_tenant(client: AsyncClient) -> None:
    headers = await _headers()
    headers.pop("Content-Type", None)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    buffer = BytesIO()
    Image.new("RGBA", (80, 40), (255, 0, 0, 255)).save(buffer, format="PNG")
    buffer.seek(0)
    files = {"file": ("logo.png", buffer, "image/png")}
    resp = await client.post(
        f"{PLATFORM_ENDPOINT}/{tenant_id}/logo",
        headers=headers,
        files=files,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["logo_url"]
    assert body["logo_meta"]["height"] <= 32


@pytest.mark.anyio
async def test_team_branding_patch_updates_label(client: AsyncClient) -> None:
    headers = await _headers(role="administrator", include_tenant=True)
    resp = await client.patch(
        f"{TEAM_ENDPOINT}/branding",
        headers=headers,
        json={"workspace_label": "Tenant Workspace"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["workspace_label"] == "Tenant Workspace"


@pytest.mark.anyio
async def test_usage_counts_ignore_inactive_users(client: AsyncClient) -> None:
    headers = await _headers(role="administrator", include_tenant=True)
    data = await _init_data()

    before_resp = await client.get(TEAM_ENDPOINT, headers=headers)
    assert before_resp.status_code == 200, before_resp.text
    before_usage = before_resp.json()["usage"]
    assert before_usage["viewer_count"] >= 1

    deactivate_resp = await client.post(
        f"{ADMIN_USERS_ENDPOINT}/{data['viewer_id']}/deactivate",
        headers=headers,
    )
    assert deactivate_resp.status_code == 200, deactivate_resp.text

    after_resp = await client.get(TEAM_ENDPOINT, headers=headers)
    assert after_resp.status_code == 200, after_resp.text
    after_usage = after_resp.json()["usage"]
    assert after_usage["viewer_count"] == max(0, before_usage["viewer_count"] - 1)

    await client.post(
        f"{ADMIN_USERS_ENDPOINT}/{data['viewer_id']}/activate",
        headers=headers,
    )


@pytest.mark.anyio
async def test_team_branding_logo_upload(client: AsyncClient) -> None:
    headers = await _headers(role="administrator", include_tenant=True)
    headers.pop("Content-Type", None)
    buffer = BytesIO()
    Image.new("RGBA", (64, 64), (0, 128, 255, 255)).save(buffer, format="PNG")
    buffer.seek(0)
    files = {"file": ("logo.png", buffer, "image/png")}
    resp = await client.post(
        f"{TEAM_ENDPOINT}/branding/logo",
        headers=headers,
        files=files,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["logo_url"]


@pytest.mark.anyio
async def test_create_tenant_admin_endpoint(client: AsyncClient) -> None:
    headers = await _headers()
    data = await _init_data()
    payload = {
        "email": "client.admin@example.com",
        "full_name": "Client Admin",
        "password": "Admin123!",
    }
    resp = await client.post(
        f"{PLATFORM_ENDPOINT}/{data['tenant_id']}/admins",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == payload["email"]

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == payload["email"]))
        assert user is not None
        assert user.tenant_id == data["tenant_id"]
        assert user.role.value == "administrator"


@pytest.mark.anyio
async def test_create_tenant_with_initial_admin(client: AsyncClient) -> None:
    headers = await _headers()
    slug = f"tenant-{uuid4().hex[:8]}"
    payload = {
        "name": f"Tenant {slug}",
        "slug": slug,
        "type": "company",
        "status": "active",
        "client_portal_enabled": True,
        "status_sharing_allowed": False,
        "description": None,
        "settings": {},
        "license": {
            "plan": "company_basic",
            "max_recruiters": 5,
            "max_supervisors": 2,
            "max_client_managers": 1,
            "max_viewers": 3,
            "max_storage_gb": 5,
            "max_companies": 5,
            "auto_renew": True,
        },
        "initial_admin": {
            "email": f"{slug}@tenant.dev",
            "full_name": "Initial Admin",
            "password": "Admin123!",
        },
    }
    resp = await client.post(PLATFORM_ENDPOINT, headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    tenant_body = resp.json()
    tenant_id = tenant_body["id"]

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == payload["initial_admin"]["email"]))
        assert user is not None
        assert str(user.tenant_id) == tenant_id


@pytest.mark.anyio
async def test_platform_can_toggle_modules(client: AsyncClient) -> None:
    headers = await _headers()
    data = await _init_data()
    tenant_id = data["tenant_id"]
    resp = await client.get(PLATFORM_MODULES.format(tenant_id=tenant_id), headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["candidates"] is True

    patch = {"leads": False, "client_portal": False}
    resp = await client.patch(
        PLATFORM_MODULES.format(tenant_id=tenant_id),
        headers=headers,
        json=patch,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["leads"] is False
    assert updated["client_portal"] is False


@pytest.mark.anyio
async def test_platform_can_resolve_seat_request(client: AsyncClient) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    admin_headers = await _headers(role="administrator", include_tenant=True)
    payload = {"role": "viewer", "requested_count": 2, "message": "Need access"}
    resp = await client.post(f"{TEAM_ENDPOINT}/seat-requests", headers=admin_headers, json=payload)
    assert resp.status_code == 201, resp.text
    request_id = resp.json()["id"]

    headers = await _headers()
    resp = await client.get(PLATFORM_SEAT_REQUESTS.format(tenant_id=tenant_id), headers=headers)
    assert resp.status_code == 200, resp.text
    history = resp.json()
    assert any(item["id"] == request_id for item in history)

    decision = {"status": "approved", "resolution_notes": "Granted"}
    resp = await client.post(
        f"{PLATFORM_SEAT_REQUESTS.format(tenant_id=tenant_id)}/{request_id}/decision",
        headers=headers,
        json=decision,
    )
    assert resp.status_code == 200, resp.text
    resolved = resp.json()
    assert resolved["status"] == "approved"
    assert resolved["resolution_notes"] == "Granted"
