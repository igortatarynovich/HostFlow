"""Postgres integration: superadmin cross-tenant DB bind requires audited elevated headers."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.tests.conftest import _build_token, _init_data

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
async def test_superadmin_cross_tenant_without_elevated_reason_returns_400(client: AsyncClient) -> None:
    await _ensure_agency_tenant_row(TENANT_2_ID, name="Elevated bind tenant 2", slug="elevated-t2")
    data = await _init_data()
    token = _build_token(data["admin_id"], data["admin_email"], "superadmin", data["tenant_id"])
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": TENANT_2_ID}
    resp = await client.get("/api/v1/companies", headers=headers)
    assert resp.status_code == 400, resp.text
    assert "X-HostFlow-Elevated-Reason" in str(resp.json().get("detail", ""))


@pytest.mark.anyio
async def test_superadmin_cross_tenant_with_elevated_headers_ok(client: AsyncClient) -> None:
    await _ensure_agency_tenant_row(TENANT_2_ID, name="Elevated bind tenant 2", slug="elevated-t2")
    data = await _init_data()
    token = _build_token(data["admin_id"], data["admin_email"], "superadmin", data["tenant_id"])
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": TENANT_2_ID,
        "X-HostFlow-Elevated-Reason": "security-integration-test",
        "X-HostFlow-Elevated-Scope": "cross_tenant_rls",
    }
    resp = await client.get("/api/v1/companies", headers=headers)
    assert resp.status_code == 200, resp.text
