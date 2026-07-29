"""Phase 5 — SUPERADMIN impersonation: mandatory reason + time-bound JWT."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.security.canonical_emit import emit_security_event_v1
from backend.app.security.constants import IMPERSONATION_TTL_MINUTES
from backend.app.security.event_taxonomy import EVENT_SUPERADMIN_IMPERSONATION_STARTED
from backend.tests.conftest import _build_token, _init_data

PLATFORM_TENANTS = "/api/v1/platform/tenants"
TENANT_2_ID = "22222222-2222-2222-2222-222222222222"

pytestmark = pytest.mark.postgres_integration


async def _ensure_agency_tenant_row(tenant_id: str, *, name: str, slug: str) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                INSERT INTO tenants (id, name, slug, api_key, is_active, type, status)
                VALUES (:id, :name, :slug, :api_key, true, 'agency', 'active')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": tenant_id, "name": name, "slug": slug, "api_key": uuid.uuid4().hex[:32]},
        )
        await session.commit()


@pytest.mark.anyio
async def test_impersonate_requires_reason(client: AsyncClient) -> None:
    await _ensure_agency_tenant_row(
        TENANT_2_ID, name="Phase5 tenant", slug=f"phase5-{uuid.uuid4().hex[:8]}"
    )
    data = await _init_data()
    sa_token = _build_token(data["admin_id"], data["admin_email"], "superadmin", data["tenant_id"])
    h = {"Authorization": f"Bearer {sa_token}", "Content-Type": "application/json"}

    resp = await client.post(f"{PLATFORM_TENANTS}/{TENANT_2_ID}/impersonate", headers=h, json={})
    assert resp.status_code == 422, resp.text

    resp2 = await client.post(
        f"{PLATFORM_TENANTS}/{TENANT_2_ID}/impersonate",
        headers=h,
        json={"reason": "ab"},
    )
    assert resp2.status_code == 422, resp2.text


@pytest.mark.anyio
async def test_impersonate_with_reason_emits_event_and_sets_session_kind(
    client: AsyncClient,
) -> None:
    await _ensure_agency_tenant_row(
        TENANT_2_ID, name="Phase5 tenant b", slug=f"phase5b-{uuid.uuid4().hex[:8]}"
    )
    data = await _init_data()
    sa_token = _build_token(data["admin_id"], data["admin_email"], "superadmin", data["tenant_id"])
    h = {"Authorization": f"Bearer {sa_token}", "Content-Type": "application/json"}

    with patch(
        "backend.app.security.canonical_emit.emit_security_event_v1",
        wraps=emit_security_event_v1,
    ) as mocked:
        resp = await client.post(
            f"{PLATFORM_TENANTS}/{TENANT_2_ID}/impersonate",
            headers=h,
            json={"reason": "support ticket HF-123"},
        )
        assert resp.status_code == 200, resp.text
        assert mocked.called
        kwargs = mocked.call_args.kwargs
        assert kwargs["event_type"] == EVENT_SUPERADMIN_IMPERSONATION_STARTED
        assert kwargs["extra"]["elevated_reason"] == "support ticket HF-123"
        assert kwargs["extra"]["ttl_minutes"] == IMPERSONATION_TTL_MINUTES

    body = resp.json()
    assert "token" in body

    who = await client.get(
        "/api/v1/auth/whoami-verify",
        headers={"Authorization": f"Bearer {body['token']}", "X-Tenant-Id": TENANT_2_ID},
    )
    assert who.status_code == 200, who.text
    w = who.json()
    assert w.get("session_kind") == "impersonation"
    assert w.get("tenant_id") == TENANT_2_ID
    assert w.get("impersonated_by") == data["tenant_id"]
    assert IMPERSONATION_TTL_MINUTES == 30
    assert int(w.get("exp") or 0) > int(w.get("iat") or 0)
