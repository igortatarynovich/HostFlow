"""Stage 3 slice 1 — product convert wires to convert_sales_inquiry_mapping."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_SALES_INQUIRY,
    RESULT_SALES_INQUIRY,
)
from backend.app.acquisition.flights.destination_registry import DESTINATION_SALES
from backend.app.models import ClientAccount
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED, FlightDispatchLedger
from backend.app.models.own_company import OwnCompany
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.applications import mutations
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.sales.services.ambiguous_match_review import (
    AmbiguityCandidateRef,
    ReviewDecision,
    mark_unique_match_not_required,
    open_ambiguous_match_review,
    resolve_ambiguous_match_review,
)
from backend.app.modules.sales.services.convert_mapping import CONVERT_MAPPING_KEY


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    own_company_id = row.scalar_one_or_none()
    if own_company_id is None:
        own_company_id = str(uuid.uuid4())
        db.add(OwnCompany(id=own_company_id, tenant_id=tenant_id, name=f"OC {uuid.uuid4().hex[:6]}"))
        await db.flush()
    return str(own_company_id)


async def _seed_product_bundle(db, *, tenant_id: str, suffix: str):
    own_company_id = await _own_company_id(db, tenant_id)
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized={
            "company_name": f"Transport {suffix}",
            "email": f"client-{suffix}@example.com",
            "phone": f"+48{uuid.uuid4().int % 10**9:09d}",
            "full_name": f"Contact {suffix}",
            "need": {"industry": "logistics", "budget": "10k"},
        },
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )
    inquiry = SalesInquiry(
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        status="open",
        source="public_intake",
        own_company_id=own_company_id,
        form_id=f"form-{suffix}",
        meta={"intake_result_v1": {"route_intent": "sales_inquiry", "destination": DESTINATION_SALES}},
    )
    db.add(inquiry)
    await db.flush()
    ledger_id = str(uuid.uuid4())
    db.add(
        FlightDispatchLedger(
            id=ledger_id,
            tenant_id=tenant_id,
            idempotency_key=f"flights.dispatch:{tenant_id}:{lead.id}:sales_inquiry:{suffix}",
            transport_lead_id=str(lead.id),
            route_intent="sales_inquiry",
            destination=DESTINATION_SALES,
            dispatcher_id=DISPATCHER_SALES_INQUIRY,
            status=STATUS_CONFIRMED,
            module_owner=DESTINATION_SALES,
            result_type=RESULT_SALES_INQUIRY,
            result_id=str(inquiry.id),
            confirmed_at=datetime.now(timezone.utc),
        )
    )
    await db.flush()
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        own_company_id=own_company_id,
        actor_id="seed-actor",
    )
    await db.refresh(inquiry)
    return lead, inquiry, ledger_id, own_company_id


@pytest.mark.asyncio
async def test_product_convert_uses_mapping_and_is_idempotent(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead, inquiry, _ledger_id, own_company_id = await _seed_product_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    user = SimpleNamespace(sub="actor-product-1", role="manager")

    first = await mutations.convert_sales_inquiry(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        application_id=str(lead.id),
        current_user=user,  # type: ignore[arg-type]
    )
    await db.refresh(inquiry)
    assert inquiry.status == "converted"
    assert inquiry.meta[CONVERT_MAPPING_KEY]["client_account_id"]
    account_id = inquiry.meta[CONVERT_MAPPING_KEY]["client_account_id"]
    assert first.id == str(lead.id)

    second = await mutations.convert_sales_inquiry(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        application_id=str(lead.id),
        current_user=user,  # type: ignore[arg-type]
    )
    await db.refresh(inquiry)
    assert inquiry.meta[CONVERT_MAPPING_KEY]["client_account_id"] == account_id
    assert second.id == str(lead.id)

    account_count = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == str(lead.id))
    )
    assert account_count == 1


@pytest.mark.asyncio
async def test_product_convert_applies_match_existing(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead, inquiry, ledger_id, own_company_id = await _seed_product_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    existing = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        display_name=f"Existing {suffix}",
        status="prospect",
    )
    other = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        display_name=f"Other {suffix}",
        status="prospect",
    )
    db.add_all([existing, other])
    await db.flush()

    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(existing.id)),
            AmbiguityCandidateRef(client_account_id=str(other.id)),
        ],
        own_company_id=own_company_id,
    )
    await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        decision=ReviewDecision(action="match_existing", client_account_id=str(existing.id)),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    await db.commit()

    user = SimpleNamespace(sub="actor-product-2", role="manager")
    await mutations.convert_sales_inquiry(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        application_id=str(lead.id),
        current_user=user,  # type: ignore[arg-type]
    )
    await db.refresh(inquiry)
    await db.refresh(lead)

    assert inquiry.meta[CONVERT_MAPPING_KEY]["client_account_id"] == str(existing.id)
    assert inquiry.meta[CONVERT_MAPPING_KEY]["review_decision"]["action"] == "match_existing"
    assert str(lead.client_account_id) == str(existing.id)

    created_from_lead = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == str(lead.id))
    )
    assert created_from_lead == 0


@pytest.mark.asyncio
async def test_product_convert_blocks_unresolved_review(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead, inquiry, ledger_id, own_company_id = await _seed_product_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    a1 = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        display_name=f"A1 {suffix}",
        status="prospect",
    )
    a2 = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        display_name=f"A2 {suffix}",
        status="prospect",
    )
    db.add_all([a1, a2])
    await db.flush()
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )
    await db.commit()

    user = SimpleNamespace(sub="actor-product-3", role="manager")
    with pytest.raises(HTTPException) as exc:
        await mutations.convert_sales_inquiry(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            application_id=str(lead.id),
            current_user=user,  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 422
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("reason") == "unresolved_review"
