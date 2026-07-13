"""GET /recruitment/applications — recruitment inbox list."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, OwnCompany
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
        own_company_id = str(oc_row.scalar_one())
        lead_id = str(uuid.uuid4())
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={"full_name": "Dup Review Applicant", "phone": "+48111222333"},
                status="duplicate_review",
                source="website",
            )
        )
        await db.commit()

    resp = await client.get(
        "/api/v1/recruitment/applications",
        headers={**manager_headers, "X-Own-Company-Id": own_company_id},
        params={"limit": 200, "scope": "all"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids = {item["id"] for item in body["items"]}
    assert lead_id in ids
    item = next(row for row in body["items"] if row["id"] == lead_id)
    assert item["status"] == "in_progress"
    assert item["tab_bucket"] == "in_progress"


@pytest.mark.anyio
async def test_list_recruitment_applications_includes_completed_lead(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        oc_row = await db.execute(
            select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()).limit(1)
        )
        own_company_id = str(oc_row.scalar_one())
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                first_name="Done",
                last_name="Applicant",
                email=f"done-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                lead_type="candidate",
                company_id=company_id,
                candidate_id=cand_id,
                payload={},
                normalized={"full_name": "Done Applicant", "phone": "+48123456789"},
                status="processed",
                source="website",
            )
        )
        await db.commit()

    resp_all = await client.get(
        "/api/v1/recruitment/applications",
        headers={**manager_headers, "X-Own-Company-Id": own_company_id},
        params={"limit": 200, "scope": "all"},
    )
    assert resp_all.status_code == 200, resp_all.text
    body = resp_all.json()
    item = next((row for row in body["items"] if row["id"] == lead_id), None)
    assert item is not None, body["items"]
    assert item["status"] == "completed"
    assert item["tab_bucket"] == "completed"
    assert item["outcome_entity_id"] == cand_id

    resp_open = await client.get(
        "/api/v1/recruitment/applications",
        headers={**manager_headers, "X-Own-Company-Id": own_company_id},
        params={"limit": 200, "scope": "open"},
    )
    assert resp_open.status_code == 200, resp_open.text
    open_ids = {row["id"] for row in resp_open.json()["items"]}
    assert lead_id not in open_ids


@pytest.mark.anyio
async def test_list_recruitment_applications_tab_completed_with_counts(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        oc_row = await db.execute(
            select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()).limit(1)
        )
        own_company_id = str(oc_row.scalar_one())
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                first_name="Tab",
                last_name="Completed",
                email=f"tab-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                lead_type="candidate",
                company_id=company_id,
                candidate_id=cand_id,
                payload={},
                normalized={"full_name": "Tab Completed"},
                status="processed",
                source="website",
            )
        )
        await db.commit()

    resp = await client.get(
        "/api/v1/recruitment/applications",
        headers={**manager_headers, "X-Own-Company-Id": own_company_id},
        params={"limit": 200, "scope": "all", "tab": "completed", "include_counts": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(row["id"] == lead_id for row in body["items"])
    assert body.get("counts") is not None
    assert int(body["counts"].get("completed", 0)) >= 1
