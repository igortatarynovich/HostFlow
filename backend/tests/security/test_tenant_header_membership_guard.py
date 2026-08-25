"""P0: authenticated non-superadmin cannot bind RLS via foreign X-Tenant-Id without membership."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.tests.conftest import _build_token, _init_data

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
async def test_non_superadmin_foreign_tenant_header_forbidden(client: AsyncClient) -> None:
    # Fresh tenant id — avoid leftover memberships from other tests on shared Postgres.
    foreign_tenant = str(uuid.uuid4())
    await _ensure_agency_tenant_row(
        foreign_tenant,
        name=f"Foreign header {foreign_tenant[:8]}",
        slug=f"foreign-hdr-{foreign_tenant[:8]}",
    )
    data = await _init_data()
    token = _build_token(data["admin_id"], data["admin_email"], "administrator", data["tenant_id"])
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": foreign_tenant}
    resp = await client.get("/api/v1/companies", headers=headers)
    assert resp.status_code == 403, resp.text
    assert "Forbidden for tenant" in str(resp.json().get("detail", ""))


@pytest.mark.anyio
async def test_non_superadmin_membership_allows_header_tenant(client: AsyncClient) -> None:
    member_tenant = str(uuid.uuid4())
    await _ensure_agency_tenant_row(
        member_tenant,
        name=f"Membership header {member_tenant[:8]}",
        slug=f"member-hdr-{member_tenant[:8]}",
    )
    data = await _init_data()
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                INSERT INTO user_memberships (id, user_id, tenant_id, role)
                VALUES (:id, :user_id, :tenant_id, :role)
                ON CONFLICT (user_id, tenant_id) DO UPDATE SET role = excluded.role
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": data["admin_id"],
                "tenant_id": member_tenant,
                "role": "administrator",
            },
        )
        await session.commit()

    token = _build_token(data["admin_id"], data["admin_email"], "administrator", data["tenant_id"])
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": member_tenant}
    resp = await client.get("/api/v1/companies", headers=headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_matching_jwt_and_header_tenant_ok(client: AsyncClient) -> None:
    data = await _init_data()
    token = _build_token(data["admin_id"], data["admin_email"], "administrator", data["tenant_id"])
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": data["tenant_id"]}
    resp = await client.get("/api/v1/companies", headers=headers)
    assert resp.status_code == 200, resp.text
