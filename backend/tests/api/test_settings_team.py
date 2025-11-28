from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from httpx import AsyncClient

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.tests.conftest import _init_data

TEAM_BASE = "/api/v1/settings/team"


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


async def _headers(role: str = "administrator", include_tenant: bool = False) -> Dict[str, str]:
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
async def test_module_settings_roundtrip(client: AsyncClient) -> None:
    headers = await _headers(include_tenant=True)
    resp = await client.get(f"{TEAM_BASE}/modules", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["candidates"] is True

    patch = {"leads": False, "client_portal": False}
    resp = await client.patch(f"{TEAM_BASE}/modules", headers=headers, json=patch)
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["leads"] is False
    assert updated["client_portal"] is False

    resp = await client.get(f"{TEAM_BASE}/modules", headers=headers)
    assert resp.status_code == 200
    cached = resp.json()
    assert cached["leads"] is False
    assert cached["client_portal"] is False


@pytest.mark.anyio
async def test_seat_requests_create_and_list(client: AsyncClient) -> None:
    headers = await _headers(include_tenant=True)
    payload = {"role": "recruiter", "requested_count": 5, "message": "Need more seats"}
    resp = await client.post(f"{TEAM_BASE}/seat-requests", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    entry = resp.json()
    assert entry["role"] == "recruiter"
    assert entry["requested_count"] == 5
    assert entry["status"] == "pending"

    resp = await client.get(f"{TEAM_BASE}/seat-requests", headers=headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    assert history[0]["requested_count"] >= 1
