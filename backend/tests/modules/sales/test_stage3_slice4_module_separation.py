"""Stage 3 slice 4 — Recruitment API must not surface SalesInquiry / client Leads."""

from __future__ import annotations

import pytest

from backend.tests.modules.sales.test_stage3_slice3_product_identity import (
    _seed_recruitment_lead,
    _seed_sales_pair,
)


@pytest.mark.asyncio
async def test_recruitment_list_excludes_sales_inquiry_and_client_lead(
    client,
    manager_headers,
    db,
    tenant_id: str,
) -> None:
    lead, inquiry, own_company_id = await _seed_sales_pair(db, tenant_id=tenant_id)
    candidate = await _seed_recruitment_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        full_name="Candidate Only",
    )
    await db.commit()

    headers = {**manager_headers, "X-Own-Company-Id": own_company_id}
    rec = await client.get("/api/v1/recruitment/applications", headers=headers)
    assert rec.status_code == 200, rec.text
    rec_ids = {str(item.get("id") or "") for item in (rec.json().get("items") or [])}
    rec_modules = {
        str(item.get("id") or ""): str(item.get("module") or "")
        for item in (rec.json().get("items") or [])
    }
    assert str(candidate.id) in rec_ids
    assert rec_modules.get(str(candidate.id)) == "recruitment"
    assert str(inquiry.id) not in rec_ids
    assert str(lead.id) not in rec_ids

    sales = await client.get("/api/v1/sales/inquiries", headers=headers)
    assert sales.status_code == 200, sales.text
    sales_ids = {str(item.get("id") or "") for item in (sales.json().get("items") or [])}
    sales_transport = {
        str(item.get("transport_lead_id") or "") for item in (sales.json().get("items") or [])
    }
    assert str(inquiry.id) in sales_ids
    assert str(lead.id) in sales_transport
    assert str(candidate.id) not in sales_ids
    assert str(candidate.id) not in sales_transport
