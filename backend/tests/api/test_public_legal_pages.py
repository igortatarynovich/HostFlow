from __future__ import annotations

import uuid

import pytest
from sqlalchemy import update

from backend.app.models.legal_document import LegalDocument
from backend.app.models.tenant import Tenant
from backend.app.db.session import async_session_maker


@pytest.mark.anyio
async def test_public_legal_resolves_tenant_by_host(client):
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        tenant = Tenant(
            id=tenant_id,
            name=f"tenant-{uuid.uuid4().hex[:8]}",
            slug=f"tenant-{uuid.uuid4().hex[:8]}",
            api_key=f"k_{uuid.uuid4().hex}",
            is_active=True,
            settings={"public_hosts": ["legal-tenant-a.example.com"]},
        )
        session.add(tenant)
        await session.flush()
        session.add(
            LegalDocument(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                type="rodo_clause",
                version_id="v-host-a-1",
                content_html="<p>Tenant A RODO</p>",
                is_active=True,
            )
        )
        await session.commit()

    r = await client.get("/legal/rodo.html", headers={"Host": "legal-tenant-a.example.com"})
    assert r.status_code == 200
    assert "Tenant A RODO" in r.text
    assert "v-host-a-1" in r.text


@pytest.mark.anyio
async def test_public_legal_redirects_to_content_url(client):
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        tenant = Tenant(
            id=tenant_id,
            name=f"tenant-{uuid.uuid4().hex[:8]}-b",
            slug=f"tenant-{uuid.uuid4().hex[:8]}-b",
            api_key=f"k_{uuid.uuid4().hex}b",
            is_active=True,
            settings={"public_hosts": ["legal-tenant-b.example.com"]},
        )
        session.add(tenant)
        await session.flush()
        session.add(
            LegalDocument(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                type="rodo_clause",
                version_id="v-host-b-1",
                content_url="https://docs.example.com/rodo-v-host-b-1",
                is_active=True,
            )
        )
        await session.commit()

    r = await client.get(
        "/legal/rodo.html",
        headers={"Host": "legal-tenant-b.example.com"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers.get("location") == "https://docs.example.com/rodo-v-host-b-1"


@pytest.mark.anyio
async def test_public_legal_unknown_host_falls_back_to_default_tenant(client, tenant_id):
    async with async_session_maker() as session:
        await session.execute(
            update(LegalDocument)
            .where(LegalDocument.tenant_id == str(tenant_id))
            .where(LegalDocument.type == "rodo_clause")
            .values(is_active=False)
        )
        session.add(
            LegalDocument(
                id=str(uuid.uuid4()),
                tenant_id=str(tenant_id),
                type="rodo_clause",
                version_id="v-default-1",
                content_html="<p>Default Tenant RODO</p>",
                is_active=True,
            )
        )
        await session.commit()

    r = await client.get("/legal/rodo.html", headers={"Host": "unknown-host.example.com"}, follow_redirects=False)
    assert r.status_code == 200
    assert "Default Tenant RODO" in r.text
    assert "v-default-1" in r.text
