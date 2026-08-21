"""Recruitment application rail ops: RODO + comments on the Application facade."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Lead, OwnCompany
from backend.tests.api.test_leads_meta import _ensure_company


async def _seed_open_recruitment_lead(tenant_id: str) -> str:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        oc_row = await db.execute(
            select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()).limit(1)
        )
        own_company_id = oc_row.scalar_one_or_none()
        if own_company_id is None:
            own_company_id = uuid.uuid4()
            db.add(OwnCompany(id=own_company_id, tenant_id=tenant_id, name="Rail OC"))
            await db.commit()
        lead_id = uuid.uuid4()
        email = f"rail-{uuid.uuid4().hex[:8]}@example.com"
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                company_id=company_id,
                source="meta",
                status="new",
                stage="new",
                lead_type="candidate",
                payload={"name": "Rail Applicant"},
                normalized={"full_name": "Rail Applicant", "email": email},
            )
        )
        await db.commit()
        return str(lead_id)


@pytest.mark.anyio
async def test_recruitment_application_exposes_rodo_and_accepts_source_provided(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    lead_id = await _seed_open_recruitment_lead(tenant_id)
    got = await client.get(f"/api/v1/recruitment/applications/{lead_id}", headers=manager_headers)
    assert got.status_code == 200, got.text
    ext = got.json().get("extensions") or {}
    rodo = ext.get("rodo") or {}
    assert rodo.get("satisfied") is False
    assert rodo.get("status") in {"manual_required", "pending_channel", "pending_policy"}

    marked = await client.post(
        f"/api/v1/recruitment/applications/{lead_id}/compliance/rodo/source-provided",
        headers=manager_headers,
    )
    assert marked.status_code == 200, marked.text
    body = marked.json()
    assert body.get("ok") is True
    rodo_after = ((body.get("application") or {}).get("extensions") or {}).get("rodo") or {}
    assert rodo_after.get("satisfied") is True
    assert rodo_after.get("status") == "source_provided"


@pytest.mark.anyio
async def test_recruitment_application_comment_roundtrip(client, manager_headers, tenant_id: str) -> None:
    lead_id = await _seed_open_recruitment_lead(tenant_id)
    saved = await client.post(
        f"/api/v1/recruitment/applications/{lead_id}/comments",
        headers=manager_headers,
        json={"note": "Call back tomorrow 15:00"},
    )
    assert saved.status_code == 200, saved.text
    comments = (saved.json().get("extensions") or {}).get("comments") or []
    assert any(row.get("note") == "Call back tomorrow 15:00" for row in comments)
