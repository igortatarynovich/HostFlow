"""DELETE /api/v1/leads/{lead_id} — manual removal (e.g. test ingests)."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.db.session import async_session_maker
from backend.tests.conftest import DEFAULT_TENANT_ID, _set_tenant


@pytest.mark.asyncio
async def test_delete_lead_returns_204_and_get_404(
    client: AsyncClient,
    manager_headers: dict,
    tenant_id: str,
) -> None:
    lead_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _set_tenant(session, DEFAULT_TENANT_ID)
        row = await session.execute(
            sa.text("SELECT id FROM companies WHERE tenant_id = :t LIMIT 1"),
            {"t": tenant_id},
        )
        company_id = str(row.scalar_one())
        oc_row = await session.execute(
            sa.text("SELECT id FROM own_companies WHERE tenant_id = :t ORDER BY created_at ASC LIMIT 1"),
            {"t": tenant_id},
        )
        own_company_id = oc_row.scalar_one_or_none()
        if own_company_id:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO leads (
                      id, tenant_id, own_company_id, lead_type, company_id, source, payload, normalized, status, created_at
                    )
                    VALUES (
                      :id, :tenant_id, :own_company_id, 'candidate', :company_id, 'meta',
                      CAST(:payload AS jsonb), CAST(:normalized AS jsonb), 'needs_routing', CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": lead_id,
                    "tenant_id": tenant_id,
                    "own_company_id": str(own_company_id),
                    "company_id": company_id,
                    "payload": "{}",
                    "normalized": '{"full_name": "Delete Me Test"}',
                },
            )
        else:
            await session.execute(
                sa.text(
                    """
                    INSERT INTO leads (
                      id, tenant_id, lead_type, company_id, source, payload, normalized, status, created_at
                    )
                    VALUES (
                      :id, :tenant_id, 'candidate', :company_id, 'meta',
                      CAST(:payload AS jsonb), CAST(:normalized AS jsonb), 'needs_routing', CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": lead_id,
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "payload": "{}",
                    "normalized": '{"full_name": "Delete Me Test"}',
                },
            )
        await session.commit()

    del_resp = await client.delete(f"/api/v1/leads/{lead_id}", headers=manager_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/leads/{lead_id}", headers=manager_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_lead_viewer_forbidden(
    client: AsyncClient,
    viewer_headers: dict,
) -> None:
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/leads/{fake_id}", headers=viewer_headers)
    assert resp.status_code == 403
