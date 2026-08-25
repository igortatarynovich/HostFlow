"""Stage 3 slice 2 — Sales + Lead convert entrypoints share one mapping engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

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
from backend.app.modules.leads.router import convert_client_lead_to_client_endpoint
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


async def _seed_ready_bundle(db, *, tenant_id: str, suffix: str, stamp_review: bool = True):
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
    if stamp_review:
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
    await db.commit()
    return str(lead.id), str(inquiry.id), ledger_id, own_company_id


def _user(suffix: str = "1") -> SimpleNamespace:
    return SimpleNamespace(sub=f"actor-entry-{suffix}", role="manager")


async def _via_sales(db, *, tenant_id: str, own_company_id: str, lead_id: str, user) -> str:
    out = await mutations.convert_sales_inquiry(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        application_id=lead_id,
        current_user=user,  # type: ignore[arg-type]
    )
    return str(out.outcome_entity_id or "")


async def _via_lead(db, *, tenant_id: str, own_company_id: str, lead_id: str, user) -> str:
    out = await convert_client_lead_to_client_endpoint(
        lead_id,
        db_tenant=(db, UUID(tenant_id)),
        current_user=user,  # type: ignore[arg-type]
        own_company_id=own_company_id,
        _role="manager",
    )
    # Prefer ClientAccount id (mapping SoT); converted_client_id may be legacy Company id.
    return str(getattr(out, "client_account_id", None) or getattr(out, "converted_client_id", None) or "")


async def _mapping_client_id(db, inquiry_id: str) -> str:
    inquiry = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.id == inquiry_id)
        .execution_options(populate_existing=True)
    )
    assert inquiry is not None
    mapping = (inquiry.meta or {}).get(CONVERT_MAPPING_KEY) or {}
    return str(mapping.get("client_account_id") or "")


@pytest.mark.asyncio
async def test_sales_endpoint_creates_mapping_and_client_account(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead_id, inquiry_id, _ledger_id, own_company_id = await _seed_ready_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    client_id = await _via_sales(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_id=lead_id,
        user=_user("sales"),
    )
    assert client_id
    mapped = await _mapping_client_id(db, inquiry_id)
    assert mapped == client_id
    account = await db.scalar(select(ClientAccount).where(ClientAccount.id == client_id))
    assert account is not None
    assert str(account.source_lead_id) == lead_id


@pytest.mark.asyncio
async def test_sales_then_lead_replay_same_client_account(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead_id, inquiry_id, _ledger_id, own_company_id = await _seed_ready_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    first = await _via_sales(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_id=lead_id,
        user=_user("a"),
    )
    second = await _via_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_id=lead_id,
        user=_user("b"),
    )
    assert first and first == second
    assert await _mapping_client_id(db, inquiry_id) == first
    count = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == lead_id)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_lead_then_sales_replay_same_client_account(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead_id, inquiry_id, _ledger_id, own_company_id = await _seed_ready_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    first = await _via_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_id=lead_id,
        user=_user("c"),
    )
    second = await _via_sales(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_id=lead_id,
        user=_user("d"),
    )
    assert first and first == second
    assert await _mapping_client_id(db, inquiry_id) == first
    count = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == lead_id)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_match_existing_same_via_both_endpoints(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead_id, inquiry_id, ledger_id, own_company_id = await _seed_ready_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    existing_id = account_crud.new_client_account_id()
    other_id = account_crud.new_client_account_id()
    db.add_all(
        [
            ClientAccount(
                id=existing_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                display_name=f"Existing {suffix}",
                status="prospect",
            ),
            ClientAccount(
                id=other_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                display_name=f"Other {suffix}",
                status="prospect",
            ),
        ]
    )
    await db.flush()
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=inquiry_id,
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        candidates=[
            AmbiguityCandidateRef(client_account_id=existing_id),
            AmbiguityCandidateRef(client_account_id=other_id),
        ],
        own_company_id=own_company_id,
    )
    await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=inquiry_id,
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        decision=ReviewDecision(action="match_existing", client_account_id=existing_id),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    await db.commit()

    via_sales = await _via_sales(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_id=lead_id,
        user=_user("match-s"),
    )
    via_lead = await _via_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_id=lead_id,
        user=_user("match-l"),
    )
    assert via_sales == existing_id
    assert via_lead == existing_id
    mapped = await _mapping_client_id(db, inquiry_id)
    assert mapped == existing_id
    inquiry_row = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.id == inquiry_id)
        .execution_options(populate_existing=True)
    )
    assert inquiry_row is not None
    assert ((inquiry_row.meta or {})[CONVERT_MAPPING_KEY]["review_decision"]["action"] == "match_existing")
    created = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == lead_id)
    )
    assert created == 0


@pytest.mark.asyncio
async def test_unresolved_review_blocks_both_endpoints(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead_id, inquiry_id, ledger_id, own_company_id = await _seed_ready_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )
    a1_id = account_crud.new_client_account_id()
    a2_id = account_crud.new_client_account_id()
    db.add_all(
        [
            ClientAccount(
                id=a1_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                display_name=f"A1 {suffix}",
                status="prospect",
            ),
            ClientAccount(
                id=a2_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                display_name=f"A2 {suffix}",
                status="prospect",
            ),
        ]
    )
    await db.flush()
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=inquiry_id,
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        candidates=[
            AmbiguityCandidateRef(client_account_id=a1_id),
            AmbiguityCandidateRef(client_account_id=a2_id),
        ],
        own_company_id=own_company_id,
    )
    await db.commit()

    with pytest.raises(HTTPException) as sales_exc:
        await _via_sales(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            lead_id=lead_id,
            user=_user("block-s"),
        )
    assert sales_exc.value.status_code == 422
    assert isinstance(sales_exc.value.detail, dict)
    assert sales_exc.value.detail.get("reason") == "unresolved_review"

    with pytest.raises(HTTPException) as lead_exc:
        await _via_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            lead_id=lead_id,
            user=_user("block-l"),
        )
    assert lead_exc.value.status_code == 422
    assert isinstance(lead_exc.value.detail, dict)
    assert lead_exc.value.detail.get("reason") == "unresolved_review"


@pytest.mark.asyncio
async def test_missing_review_blocks_both_endpoints(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead_id, inquiry_id, _ledger_id, own_company_id = await _seed_ready_bundle(
        db, tenant_id=tenant_id, suffix=suffix, stamp_review=False
    )

    with pytest.raises(HTTPException) as sales_exc:
        await _via_sales(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            lead_id=lead_id,
            user=_user("miss-s"),
        )
    assert sales_exc.value.status_code == 422
    assert isinstance(sales_exc.value.detail, dict)
    assert sales_exc.value.detail.get("reason") == "missing_review_decision"

    with pytest.raises(HTTPException) as lead_exc:
        await _via_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            lead_id=lead_id,
            user=_user("miss-l"),
        )
    assert lead_exc.value.status_code == 422
    assert isinstance(lead_exc.value.detail, dict)
    assert lead_exc.value.detail.get("reason") == "missing_review_decision"
    assert await _mapping_client_id(db, inquiry_id) == ""


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sales", "lead"])
async def test_audit_failure_rolls_back_either_entrypoint(
    db, tenant_id: str, monkeypatch, entrypoint: str
) -> None:
    suffix = uuid.uuid4().hex[:8]
    lead_id, inquiry_id, _ledger_id, own_company_id = await _seed_ready_bundle(
        db, tenant_id=tenant_id, suffix=suffix
    )

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("forced audit failure")

    monkeypatch.setattr(
        "backend.app.modules.sales.services.convert_mapping.log_activity",
        _boom,
    )

    with pytest.raises(HTTPException) as exc:
        if entrypoint == "sales":
            await _via_sales(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                lead_id=lead_id,
                user=_user(f"audit-{entrypoint}"),
            )
        else:
            await _via_lead(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                lead_id=lead_id,
                user=_user(f"audit-{entrypoint}"),
            )
    assert exc.value.status_code == 422
    assert isinstance(exc.value.detail, dict)
    assert exc.value.detail.get("reason") == "audit_write_failed"

    await db.rollback()
    reloaded = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.id == inquiry_id)
        .execution_options(populate_existing=True)
    )
    assert reloaded is not None
    assert reloaded.status != "converted"
    assert CONVERT_MAPPING_KEY not in (reloaded.meta or {})
    count = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == lead_id)
    )
    assert count == 0


@pytest.mark.asyncio
async def test_either_entrypoint_produces_single_mapping_engine_result(db, tenant_id: str) -> None:
    """No separate direct-convert product path: both write the same mapping + one CA."""
    suffix_a = uuid.uuid4().hex[:8]
    suffix_b = uuid.uuid4().hex[:8]
    lead_a, inquiry_a, _l1, oc = await _seed_ready_bundle(db, tenant_id=tenant_id, suffix=suffix_a)
    lead_b, inquiry_b, _l2, _oc2 = await _seed_ready_bundle(db, tenant_id=tenant_id, suffix=suffix_b)

    sales_client_id = await _via_sales(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        lead_id=lead_a,
        user=_user("engine-s"),
    )
    lead_client_id = await _via_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        lead_id=lead_b,
        user=_user("engine-l"),
    )

    map_a = await _mapping_client_id(db, inquiry_a)
    map_b = await _mapping_client_id(db, inquiry_b)
    assert map_a == sales_client_id and map_a
    assert map_b == lead_client_id and map_b
    assert map_a != map_b

    for inquiry_id, client_id in ((inquiry_a, sales_client_id), (inquiry_b, lead_client_id)):
        inquiry = await db.scalar(
            select(SalesInquiry)
            .where(SalesInquiry.id == inquiry_id)
            .execution_options(populate_existing=True)
        )
        assert inquiry is not None
        assert inquiry.status == "converted"
        mapping = (inquiry.meta or {}).get(CONVERT_MAPPING_KEY) or {}
        assert mapping.get("client_account_id") == client_id
        assert mapping.get("review_decision")
