"""GET /recruitment/applications — recruitment inbox list."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Lead, OwnCompany
from backend.tests.api.test_leads_meta import _ensure_company


@pytest.mark.anyio
async def test_list_recruitment_applications_includes_duplicate_review_lead(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    """Regression: duplicate_review leads must not break LeadOut serialization."""
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        oc_row = await db.execute(
            select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()).limit(1)
        )
        own_company_id = oc_row.scalar_one_or_none()
        if own_company_id is None:
            own_company_id = uuid.uuid4()
            db.add(
                OwnCompany(
                    id=own_company_id,
                    tenant_id=tenant_id,
                    name="Test OC",
                )
            )
            await db.commit()

        lead_id = uuid.uuid4()
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                company_id=company_id,
                source="website",
                status="duplicate_review",
                lead_type="candidate",
                payload={"name": "Dup Review Lead"},
            )
        )
        await db.commit()

    resp = await client.get(
        "/api/v1/recruitment/applications",
        headers=manager_headers,
        params={"limit": 50},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids = {item["id"] for item in body.get("items", [])}
    assert str(lead_id) in ids
