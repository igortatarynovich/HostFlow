"""Stage 3 slice 3 — SalesInquiry product identity on Sales HTTP."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.own_company import OwnCompany
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.applications import mutations
from backend.app.modules.applications.mappers import (
    lead_to_sales_inquiry,
    sales_inquiry_to_application,
)
from backend.app.modules.applications.sales_resolve import (
    list_sales_inquiry_pairs,
    resolve_sales_inquiry_and_lead,
)
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.sales.services.capability_spine_read import (
    get_capability_spine_for_application,
)


def test_sales_inquiry_to_application_uses_si_product_id():
    lead_id = str(uuid4())
    si_id = str(uuid4())
    lead = SimpleNamespace(
        id=lead_id,
        normalized={
            "company_name_hint": "Acme Sp. z o.o.",
            "field_answers": [{"name": "custom", "values": ["1"]}],
            "additional_answers": [{"name": "custom", "values": ["1"]}],
        },
        company_name=None,
        source="meta",
        stage="new",
        status="new",
        assigned_to=None,
        recruiter_id=None,
        next_action_type=None,
        updated_at=None,
        created_at=None,
        priority=None,
        converted_client_id=None,
        client_account_id=None,
        payload={"entry": []},
        phone=None,
        email=None,
        full_name=None,
    )
    inquiry = SimpleNamespace(id=si_id)
    app = sales_inquiry_to_application(inquiry, lead)
    assert app.id == si_id
    assert app.sales_inquiry_id == si_id
    assert app.transport_lead_id == lead_id
    assert app.extensions["transport_lead_id"] == lead_id
    assert app.title == "Acme Sp. z o.o."
    assert any(row["name"] == "custom" for row in app.extensions["meta_form_answers"])
    # Sales list never projects recruitment module.
    assert app.module == "sales"

    legacy = lead_to_sales_inquiry(lead)
    assert legacy.id == lead_id
    assert legacy.transport_lead_id == lead_id


def test_lost_sales_inquiry_status_is_rejected_not_completed():
    lead_id = str(uuid4())
    lead = SimpleNamespace(
        id=lead_id,
        normalized={"company_name_hint": "Lost Co"},
        company_name=None,
        source="meta",
        stage="lost",
        status="processed",
        assigned_to=None,
        recruiter_id=None,
        next_action_type=None,
        updated_at=None,
        created_at=None,
        priority=None,
        converted_client_id=None,
        client_account_id=None,
        payload={},
        phone=None,
        email=None,
        full_name=None,
    )
    app = sales_inquiry_to_application(SimpleNamespace(id=str(uuid4())), lead)
    assert app.status == "rejected"
    assert app.tab_bucket == "completed"
    assert app.module == "sales"


def test_converted_sales_inquiry_status_stays_completed():
    lead = SimpleNamespace(
        id=str(uuid4()),
        normalized={"company_name_hint": "Won Co"},
        company_name=None,
        source="meta",
        stage="converted",
        status="processed",
        assigned_to=None,
        recruiter_id=None,
        next_action_type=None,
        updated_at=None,
        created_at=None,
        priority=None,
        converted_client_id=str(uuid4()),
        client_account_id=str(uuid4()),
        payload={},
        phone=None,
        email=None,
        full_name=None,
    )
    app = sales_inquiry_to_application(SimpleNamespace(id=str(uuid4())), lead)
    assert app.status == "completed"


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    own_company_id = row.scalar_one_or_none()
    if own_company_id is None:
        own_company_id = str(uuid4())
        db.add(OwnCompany(id=own_company_id, tenant_id=tenant_id, name=f"OC {uuid4().hex[:6]}"))
        await db.flush()
    return str(own_company_id)


async def _client_company_id(db, tenant_id: str) -> str:
    row = await db.execute(select(Company.id).where(Company.tenant_id == tenant_id).limit(1))
    company_id = row.scalar_one_or_none()
    if company_id is None:
        company_id = str(uuid4())
        db.add(Company(id=company_id, tenant_id=tenant_id, name=f"Co {uuid4().hex[:6]}"))
        await db.flush()
    return str(company_id)


async def _ensure_recruitment_lead_funnel(db, *, tenant_id: str, company_id: str) -> None:
    """create_lead assigns a company-scoped lead funnel; seed one for candidate fixtures."""
    existing = await db.scalar(
        select(Funnel.id)
        .where(
            Funnel.tenant_id == tenant_id,
            Funnel.company_id == company_id,
            Funnel.module_key == "recruitment",
            Funnel.type == "lead",
        )
        .limit(1)
    )
    if existing is not None:
        return
    db.add(
        Funnel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            company_id=company_id,
            module_key="recruitment",
            type="lead",
            name="Lead pipeline",
            is_default=True,
        )
    )
    await db.flush()


async def _seed_recruitment_lead(
    db, *, tenant_id: str, own_company_id: str, full_name: str
):
    company_id = await _client_company_id(db, tenant_id)
    await _ensure_recruitment_lead_funnel(db, tenant_id=tenant_id, company_id=company_id)
    return await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=company_id,
        vacancy_id=None,
        payload={},
        normalized={"full_name": full_name},
        source="meta",
        lead_type="candidate",
        lead_target_type="candidate",
    )


async def _seed_sales_pair(db, *, tenant_id: str):
    own_company_id = await _own_company_id(db, tenant_id)
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized={"company_name": "Acme Logistics", "email": "ops@example.com"},
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )
    inquiry = SalesInquiry(
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        status="open",
        source="meta",
        own_company_id=own_company_id,
    )
    db.add(inquiry)
    await db.flush()
    return lead, inquiry, own_company_id


@pytest.mark.asyncio
async def test_resolve_sales_inquiry_accepts_si_and_lead_keys(db, tenant_id: str) -> None:
    lead, inquiry, _own = await _seed_sales_pair(db, tenant_id=tenant_id)

    by_si = await resolve_sales_inquiry_and_lead(
        db, tenant_id=tenant_id, application_id=str(inquiry.id)
    )
    by_lead = await resolve_sales_inquiry_and_lead(
        db, tenant_id=tenant_id, application_id=str(lead.id)
    )
    assert str(by_si[0].id) == str(inquiry.id)
    assert str(by_si[1].id) == str(lead.id)
    assert str(by_lead[0].id) == str(inquiry.id)

    via_si = await mutations._reload_sales(db, tenant_id, _own, str(inquiry.id))
    via_lead = await mutations._reload_sales(db, tenant_id, _own, str(lead.id))
    assert via_si.id == str(inquiry.id)
    assert via_si.sales_inquiry_id == str(inquiry.id)
    assert via_si.transport_lead_id == str(lead.id)
    assert via_si.module == "sales"
    assert via_lead.id == via_si.id


@pytest.mark.asyncio
async def test_capability_spine_resolves_by_sales_inquiry_id(db, tenant_id: str) -> None:
    lead, inquiry, _own = await _seed_sales_pair(db, tenant_id=tenant_id)
    spine_si = await get_capability_spine_for_application(
        db, tenant_id=tenant_id, application_id=str(inquiry.id)
    )
    spine_lead = await get_capability_spine_for_application(
        db, tenant_id=tenant_id, application_id=str(lead.id)
    )
    assert spine_si["missing_sales_inquiry"] is False
    assert spine_si["sales_inquiry_id"] == str(inquiry.id)
    assert spine_lead["sales_inquiry_id"] == str(inquiry.id)


@pytest.mark.asyncio
async def test_recruitment_lead_is_not_a_sales_inquiry(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    lead = await _seed_recruitment_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        full_name="Candidate One",
    )
    await db.flush()
    with pytest.raises(LookupError):
        await resolve_sales_inquiry_and_lead(
            db, tenant_id=tenant_id, application_id=str(lead.id), ensure_if_lead=True
        )
    app = await mutations._reload_recruitment(db, tenant_id, str(lead.id))
    assert app.id == str(lead.id)
    assert app.module != "sales"


@pytest.mark.asyncio
async def test_sales_list_uses_inquiry_id_and_excludes_recruitment(db, tenant_id: str) -> None:
    lead, inquiry, own_company_id = await _seed_sales_pair(db, tenant_id=tenant_id)
    orphan = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized={"company_name": "Orphan Meta Co"},
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )
    candidate = await _seed_recruitment_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        full_name="Candidate Two",
    )
    await db.flush()

    pairs, total = await list_sales_inquiry_pairs(
        db, tenant_id=tenant_id, own_company_id=own_company_id, limit=200, offset=0
    )
    assert total >= 2
    product_ids = {str(si.id) for si, _lead in pairs}
    transport_ids = {str(row.id) for _si, row in pairs}
    assert str(inquiry.id) in product_ids
    assert str(lead.id) in transport_ids
    assert str(lead.id) not in product_ids
    assert str(orphan.id) in transport_ids
    assert str(candidate.id) not in transport_ids
    assert all(str(si.id) != str(row.id) for si, row in pairs)
    assert all(str(row.lead_type) == "client" for _si, row in pairs)


@pytest.mark.asyncio
async def test_http_sales_list_get_keyed_by_sales_inquiry(
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
        full_name="Not A Sales Row",
    )
    await db.commit()

    headers = {**manager_headers, "X-Own-Company-Id": own_company_id}
    listed = await client.get("/api/v1/sales/inquiries", headers=headers)
    assert listed.status_code == 200, listed.text
    items = listed.json().get("items") or []
    product_ids = {str(item.get("id") or "") for item in items}
    transport_ids = {str(item.get("transport_lead_id") or "") for item in items}
    assert str(inquiry.id) in product_ids
    assert str(lead.id) not in product_ids
    assert str(lead.id) in transport_ids
    assert str(candidate.id) not in product_ids
    assert str(candidate.id) not in transport_ids
    row = next(item for item in items if item["id"] == str(inquiry.id))
    assert row["sales_inquiry_id"] == str(inquiry.id)
    assert row["module"] == "sales"

    by_si = await client.get(f"/api/v1/sales/inquiries/{inquiry.id}", headers=headers)
    assert by_si.status_code == 200, by_si.text
    got = by_si.json()
    assert got["id"] == str(inquiry.id)
    assert got["transport_lead_id"] == str(lead.id)

    by_lead = await client.get(f"/api/v1/sales/inquiries/{lead.id}", headers=headers)
    assert by_lead.status_code == 200, by_lead.text
    assert by_lead.json()["id"] == str(inquiry.id)

    spine = await client.get(
        f"/api/v1/sales/inquiries/{inquiry.id}/capability-spine",
        headers=headers,
    )
    assert spine.status_code == 200, spine.text
    assert spine.json()["sales_inquiry_id"] == str(inquiry.id)
    assert spine.json()["missing_sales_inquiry"] is False

    patched = await client.patch(
        f"/api/v1/sales/inquiries/{inquiry.id}",
        headers=headers,
        json={"stage": "contacted"},
    )
    # Identity: SI key must resolve (404 would be a product-key miss).
    # 422 is Lead-projection policy (RODO / next-action), not slice 3.
    assert patched.status_code in (200, 422), patched.text
    if patched.status_code == 200:
        body = patched.json()
        assert body["id"] == str(inquiry.id)
        assert body["transport_lead_id"] == str(lead.id)

    rec_list = await client.get("/api/v1/recruitment/applications", headers=headers)
    assert rec_list.status_code == 200, rec_list.text
    rec_ids = {str(item.get("id") or "") for item in (rec_list.json().get("items") or [])}
    assert str(inquiry.id) not in rec_ids


@pytest.mark.asyncio
async def test_http_sales_list_backfill_is_durable_on_get(
    client,
    manager_headers,
    db,
    tenant_id: str,
) -> None:
    """Meta client leads without a persisted SI must survive list → GET.

    List backfills SalesInquiry in the request session. If that row is not
    committed, the inbox shows an id that GET /sales/inquiries/{id} 404s.
    """
    own_company_id = await _own_company_id(db, tenant_id)
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized={"company_name": "Backfill Logistics", "email": "ops@backfill.example"},
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )
    await db.commit()

    headers = {**manager_headers, "X-Own-Company-Id": own_company_id}
    listed = await client.get("/api/v1/sales/inquiries", headers=headers)
    assert listed.status_code == 200, listed.text
    items = listed.json().get("items") or []
    row = next(
        (item for item in items if str(item.get("transport_lead_id") or "") == str(lead.id)),
        None,
    )
    assert row is not None, "list must include the client lead after SI backfill"
    si_id = str(row.get("id") or "")
    assert si_id
    assert si_id != str(lead.id)

    got = await client.get(f"/api/v1/sales/inquiries/{si_id}", headers=headers)
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["id"] == si_id
    assert body["transport_lead_id"] == str(lead.id)
    assert body["module"] == "sales"
