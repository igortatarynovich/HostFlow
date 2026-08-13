"""Sales inquiry duplicate hints — phone/email sibling matching."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.modules.applications.sales_inquiry_duplicates import (
    find_possible_duplicate_sales_inquiries,
    phones_operational_match,
)


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        sa.select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id)
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    oid = row.scalar_one_or_none()
    if oid:
        return str(oid)
    oid = str(uuid.uuid4())
    db.add(OwnCompany(id=oid, tenant_id=tenant_id, name=f"OC {uuid.uuid4().hex[:6]}"))
    await db.flush()
    return oid


def test_phones_operational_match_last9() -> None:
    assert phones_operational_match("48785777097", "785777097")
    assert phones_operational_match("48785777097", "48785777097")
    assert not phones_operational_match("48785777097", "48111222333")


async def test_find_duplicates_by_phone(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    phone = f"+4899{uuid.uuid4().int % 10**7:07d}"
    lead_a = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_type="client",
        lead_target_type="client_lead",
        source="meta",
        status="new",
        payload={},
        normalized={"phone": phone, "email": f"a-{uuid.uuid4().hex[:6]}@example.com", "company_name": "Essa"},
    )
    lead_b = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_type="client",
        lead_target_type="client_lead",
        source="meta",
        status="new",
        payload={},
        normalized={
            "phone": phone,
            "email": f"b-{uuid.uuid4().hex[:6]}@example.com",
            "company_name": "Madel Transport",
        },
    )
    db.add_all([lead_a, lead_b])
    await db.flush()

    hits = await find_possible_duplicate_sales_inquiries(
        db, tenant_id=tenant_id, lead=lead_a, own_company_id=own_company_id
    )
    assert len(hits) == 1
    app, reason = hits[0]
    assert app.transport_lead_id == str(lead_b.id)
    assert app.sales_inquiry_id == app.id
    assert app.id != str(lead_b.id)
    assert reason == "phone"


async def test_find_duplicates_by_email(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    shared = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    lead_a = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_type="client",
        lead_target_type="client_lead",
        source="meta",
        status="new",
        payload={},
        normalized={"email": shared, "company_name": "A"},
    )
    lead_b = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_type="client",
        lead_target_type="client_lead",
        source="meta",
        status="new",
        payload={},
        normalized={"email": shared, "company_name": "B"},
    )
    db.add_all([lead_a, lead_b])
    await db.flush()

    hits = await find_possible_duplicate_sales_inquiries(
        db, tenant_id=tenant_id, lead=lead_a, own_company_id=own_company_id
    )
    assert len(hits) == 1
    assert hits[0][1] == "email"
    assert hits[0][0].transport_lead_id == str(lead_b.id)
    assert hits[0][0].id != str(lead_b.id)
