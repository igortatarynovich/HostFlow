"""ADR-022 Phase 2 — SalesInquiry immutable lineage tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_SALES_INQUIRY,
    RESULT_SALES_INQUIRY,
)
from backend.app.acquisition.flights.destination_registry import DESTINATION_SALES
from backend.app.models import ClientAccount
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED, FlightDispatchLedger
from backend.app.models.own_company import OwnCompany
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.sales.services.ambiguous_match_review import (
    AmbiguityCandidateRef,
    ReviewDecision,
    mark_unique_match_not_required,
    open_ambiguous_match_review,
    resolve_ambiguous_match_review,
)
from backend.app.modules.sales.services.convert_mapping import (
    CONVERT_MAPPING_KEY,
    ConvertMappingError,
    convert_sales_inquiry_mapping,
)
from backend.app.modules.sales.services.sales_inquiry_traceability import (
    LINEAGE_KEY,
    SalesInquiryTraceabilityError,
    get_lineage_for_client_account,
    get_lineage_for_sales_inquiry,
    lineage_has_review,
    record_lineage_after_convert,
)


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


async def _seed_inquiry(
    db,
    *,
    tenant_id: str,
    suffix: str,
) -> tuple[SalesInquiry, str, str]:
    own_company_id = await _own_company_id(db, tenant_id)
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized={
            "company_name": f"Co {suffix}",
            "email": f"c-{suffix}@example.com",
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
        status="received",
        source="public_intake",
        own_company_id=own_company_id,
        meta={"intake_result_v1": {"destination": DESTINATION_SALES}},
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
    return inquiry, ledger_id, own_company_id


async def _client_account(db, *, tenant_id: str, own_company_id: str, suffix: str) -> ClientAccount:
    account = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        display_name=f"Acc {suffix}",
        status="prospect",
    )
    db.add(account)
    await db.flush()
    return account


@pytest.mark.asyncio
async def test_trace_created_after_convert(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )

    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    await db.refresh(inquiry)

    assert result.traceability_refs["lineage"]["client_account_id"] == result.client_account_id
    lineage = await get_lineage_for_sales_inquiry(
        db, tenant_id=tenant_id, sales_inquiry_id=str(inquiry.id)
    )
    assert lineage["flights_ledger_id"] == ledger_id
    assert lineage["sales_inquiry_id"] == str(inquiry.id)
    assert [n["link"] for n in lineage["chain"]] == [
        "sales_inquiry",
        "flights_dispatch",
        "convert_mapping",
        "client_account",
    ]
    assert lineage_has_review(lineage) is False


@pytest.mark.asyncio
async def test_repeat_convert_does_not_create_second_trace(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    first = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    frozen = dict(first.traceability_refs["lineage"])

    second = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    await db.refresh(inquiry)

    assert second.idempotent_replay is True
    assert second.traceability_refs["lineage"] == frozen
    assert inquiry.meta[LINEAGE_KEY] == frozen


@pytest.mark.asyncio
async def test_lineage_fully_restored_from_inquiry_and_account(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()

    by_inquiry = await get_lineage_for_sales_inquiry(
        db, tenant_id=tenant_id, sales_inquiry_id=str(inquiry.id)
    )
    by_account = await get_lineage_for_client_account(
        db, tenant_id=tenant_id, client_account_id=result.client_account_id
    )
    assert by_inquiry == by_account
    assert by_inquiry["chain"][0]["id"] == str(inquiry.id)
    assert by_inquiry["chain"][-1]["id"] == result.client_account_id
    # Each link points to previous
    assert by_inquiry["chain"][1]["prev"] == f"sales_inquiry:{inquiry.id}"
    assert by_inquiry["chain"][2]["prev"] == f"flights_dispatch:{ledger_id}"


@pytest.mark.asyncio
async def test_lineage_immutable(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    frozen = dict(result.traceability_refs["lineage"])

    # Attempt rewrite via record_lineage_after_convert — must replay same doc.
    await db.refresh(inquiry)
    replay = await record_lineage_after_convert(
        db,
        tenant_id=tenant_id,
        inquiry=inquiry,
        convert_mapping=dict(inquiry.meta[CONVERT_MAPPING_KEY]),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        actor_id="other-actor",
    )
    assert replay.idempotent_replay is True
    assert replay.lineage == frozen
    assert replay.lineage.get("created_by") == frozen.get("created_by")


@pytest.mark.asyncio
async def test_review_absent_when_not_required(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    lineage = result.traceability_refs["lineage"]
    assert lineage["review"] is None
    assert lineage_has_review(lineage) is False
    assert "review_decision" not in [n["link"] for n in lineage["chain"]]


@pytest.mark.asyncio
async def test_review_present_after_ambiguity(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
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
    await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        decision=ReviewDecision(action="create_new"),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    lineage = result.traceability_refs["lineage"]
    assert lineage_has_review(lineage) is True
    assert lineage["review"]["status"] == "resolved_create_new"
    links = [n["link"] for n in lineage["chain"]]
    assert links == [
        "sales_inquiry",
        "flights_dispatch",
        "review_decision",
        "convert_mapping",
        "client_account",
    ]


@pytest.mark.asyncio
async def test_provenance_mismatch_on_lineage(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    # Stamp convert mapping only (simulate partial state), then lineage with wrong ledger.
    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    # Fresh path for mismatch: build mapping dict with different ledger id
    await db.refresh(inquiry)
    mapping = dict(inquiry.meta[CONVERT_MAPPING_KEY])
    mapping["flights_ledger_id"] = str(uuid.uuid4())
    # Clear lineage to force re-stamp attempt
    meta = dict(inquiry.meta)
    meta.pop(LINEAGE_KEY, None)
    inquiry.meta = meta
    flag_modified(inquiry, "meta")
    await db.flush()

    with pytest.raises(SalesInquiryTraceabilityError) as exc:
        await record_lineage_after_convert(
            db,
            tenant_id=tenant_id,
            inquiry=inquiry,
            convert_mapping=mapping,
            destination=DESTINATION_SALES,
            flights_ledger_id=ledger_id,
        )
    assert exc.value.reason == "provenance_mismatch"
    assert result.client_account_id


@pytest.mark.asyncio
async def test_cross_tenant_lineage_lookup_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()

    with pytest.raises(SalesInquiryTraceabilityError) as exc:
        await get_lineage_for_client_account(
            db,
            tenant_id=str(uuid.uuid4()),
            client_account_id=result.client_account_id,
        )
    assert exc.value.reason == "cross_tenant"


@pytest.mark.asyncio
async def test_orphan_convert_without_lineage_replay_fails(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
    )
    await db.commit()
    await db.refresh(inquiry)
    meta = dict(inquiry.meta)
    meta.pop(LINEAGE_KEY, None)
    inquiry.meta = meta
    flag_modified(inquiry, "meta")
    await db.flush()

    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=ledger_id,
        )
    assert exc.value.reason == "orphan_convert"


@pytest.mark.asyncio
async def test_orphan_trace_read_fails(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, _, _ = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    with pytest.raises(SalesInquiryTraceabilityError) as exc:
        await get_lineage_for_sales_inquiry(
            db, tenant_id=tenant_id, sales_inquiry_id=str(inquiry.id)
        )
    assert exc.value.reason == "orphan_trace"


@pytest.mark.asyncio
async def test_orphan_trace_for_unknown_account(db, tenant_id: str) -> None:
    with pytest.raises(SalesInquiryTraceabilityError) as exc:
        await get_lineage_for_client_account(
            db,
            tenant_id=tenant_id,
            client_account_id=str(uuid.uuid4()),
        )
    assert exc.value.reason == "orphan_trace"
