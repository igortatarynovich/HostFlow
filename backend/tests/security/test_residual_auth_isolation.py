"""Residual isolation: routes that previously bound tenant without requiring auth."""

from __future__ import annotations

import secrets
import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.tests.conftest import _build_token, _init_data

pytestmark = pytest.mark.postgres_integration


@pytest.mark.anyio
async def test_managers_endpoints_require_auth(client: AsyncClient) -> None:
    data = await _init_data()
    tenant = data["tenant_id"]
    headers = {"X-Tenant-Id": tenant}
    for path in ("/api/v1/users/managers", "/api/v1/catalogs/managers"):
        resp = await client.get(path, headers=headers)
        assert resp.status_code in (401, 403), (path, resp.status_code, resp.text)


@pytest.mark.anyio
async def test_managers_endpoints_ok_with_auth(client: AsyncClient) -> None:
    data = await _init_data()
    token = _build_token(data["admin_id"], data["admin_email"], "administrator", data["tenant_id"])
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": data["tenant_id"]}
    for path in ("/api/v1/users/managers", "/api/v1/catalogs/managers"):
        resp = await client.get(path, headers=headers)
        assert resp.status_code == 200, (path, resp.text)
        assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_analytics_overview_requires_auth(client: AsyncClient) -> None:
    data = await _init_data()
    resp = await client.get(
        "/api/v1/analytics/overview",
        headers={"X-Tenant-Id": data["tenant_id"]},
    )
    assert resp.status_code in (401, 403), resp.text


@pytest.mark.anyio
async def test_calendar_list_and_reconcile_require_auth(client: AsyncClient) -> None:
    data = await _init_data()
    headers = {"X-Tenant-Id": data["tenant_id"]}
    list_resp = await client.get("/api/v1/calendar/items", headers=headers)
    assert list_resp.status_code in (401, 403), list_resp.text
    reconcile = await client.post(
        "/api/v1/calendar/integrations/reconcile",
        headers=headers,
        json={},
    )
    assert reconcile.status_code in (401, 403), reconcile.text


@pytest.mark.anyio
async def test_meta_stages_anonymous_ignores_foreign_tenant_header(client: AsyncClient) -> None:
    """Anonymous /meta/stages must not load another tenant's funnel via X-Tenant-Id alone."""
    foreign_tenant = str(uuid.uuid4())
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
            {
                "id": foreign_tenant,
                "name": f"Anon stages {foreign_tenant[:8]}",
                "slug": f"anon-stages-{foreign_tenant[:8]}",
                "api_key": uuid.uuid4().hex[:32],
            },
        )
        await session.commit()

    resp = await client.get(
        "/api/v1/meta/stages",
        headers={"X-Tenant-Id": foreign_tenant},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("custom_stages") in ([], None) or body.get("custom_stages") == []
    assert body.get("funnel_id") in (None, "")


@pytest.mark.anyio
async def test_candidate_links_get_requires_auth(client: AsyncClient) -> None:
    data = await _init_data()
    cand_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/candidate-links/{cand_id}",
        headers={"X-Tenant-Id": data["tenant_id"]},
    )
    assert resp.status_code in (401, 403), resp.text


@pytest.mark.anyio
async def test_public_goals_resolves_tenant_from_share_token(client: AsyncClient) -> None:
    data = await _init_data()
    share_token = secrets.token_urlsafe(24)
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                UPDATE tenants
                SET status_sharing_allowed = true,
                    settings = COALESCE(settings::jsonb, '{}'::jsonb)
                      || jsonb_build_object('goals_share_token', CAST(:tok AS text))
                WHERE id = :tid
                """
            ),
            {"tok": share_token, "tid": data["tenant_id"]},
        )
        await session.commit()

    # Wrong X-Tenant-Id must not matter — token resolves the real tenant.
    wrong_tenant = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/public/goals/{share_token}",
        headers={"X-Tenant-Id": wrong_tenant},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "metrics" in body
    assert "goals" in body


@pytest.mark.anyio
async def test_document_templates_and_legal_active_require_auth(client: AsyncClient) -> None:
    data = await _init_data()
    headers = {"X-Tenant-Id": data["tenant_id"]}
    for path in (
        "/api/v1/documents/templates",
        "/api/v1/legal-documents/active",
        "/api/v1/db/document-types",
        "/api/v1/notifications/templates",
    ):
        resp = await client.get(path, headers=headers)
        assert resp.status_code in (401, 403), (path, resp.status_code, resp.text)


@pytest.mark.anyio
async def test_document_templates_ok_with_auth(client: AsyncClient) -> None:
    data = await _init_data()
    token = _build_token(data["admin_id"], data["admin_email"], "administrator", data["tenant_id"])
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": data["tenant_id"]}
    resp = await client.get("/api/v1/documents/templates", headers=headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    legal = await client.get("/api/v1/legal-documents/active", headers=headers)
    assert legal.status_code == 200, legal.text
