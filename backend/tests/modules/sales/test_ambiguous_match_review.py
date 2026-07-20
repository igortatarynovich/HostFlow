"""ADR-022 Phase 2 — SalesInquiry ambiguous match review tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_SALES_INQUIRY,
    RESULT_SALES_INQUIRY,
)
from backend.app.acquisition.flights.destination_registry import DESTINATION_RECRUITMENT, DESTINATION_SALES
from backend.app.models import ClientAccount
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED, FlightDispatchLedger
from backend.app.models.own_company import OwnCompany
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.sales.services.ambiguous_match_review import (
    REVIEW_KEY,
    STATUS_NOT_REQUIRED,
    STATUS_REQUIRED,
    STATUS_RESOLVED_CREATE_NEW,
    STATUS_RESOLVED_MATCH,
    AmbiguousMatchReviewError,
    AmbiguityCandidateRef,
    ReviewDecision,
    mark_unique_match_not_required,
    open_ambiguous_match_review,
    resolve_ambiguous_match_review,
    review_blocks_convert,
)
from backend.app.modules.sales.services.convert_mapping import (
    ConvertMappingError,
    convert_sales_inquiry_mapping,
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


async def _client_account(
    db,
    *,
    tenant_id: str,
    own_company_id: str,
    suffix: str,
) -> ClientAccount:
    account = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        display_name=f"Account {suffix}",
        status="prospect",
    )
    db.add(account)
    await db.flush()
    return account


async def _seed_inquiry(
    db,
    *,
    tenant_id: str,
    suffix: str,
    ledger_destination: str = DESTINATION_SALES,
    create_ledger: bool = True,
) -> tuple[SalesInquiry, str | None, str]:
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
        meta={"intake_result_v1": {"destination": DESTINATION_SALES, "route_intent": "sales_inquiry"}},
    )
    db.add(inquiry)
    await db.flush()

    ledger_id: str | None = None
    if create_ledger:
        ledger_id = str(uuid.uuid4())
        db.add(
            FlightDispatchLedger(
                id=ledger_id,
                tenant_id=tenant_id,
                idempotency_key=f"flights.dispatch:{tenant_id}:{lead.id}:sales_inquiry:{suffix}",
                transport_lead_id=str(lead.id),
                route_intent="sales_inquiry",
                destination=ledger_destination,
                dispatcher_id=DISPATCHER_SALES_INQUIRY,
                status=STATUS_CONFIRMED,
                module_owner=ledger_destination if ledger_destination == DESTINATION_SALES else "recruitment",
                result_type=RESULT_SALES_INQUIRY if ledger_destination == DESTINATION_SALES else "application",
                result_id=str(inquiry.id),
                confirmed_at=datetime.now(timezone.utc),
            )
        )
        await db.flush()
    return inquiry, ledger_id, own_company_id


@pytest.mark.asyncio
async def test_ambiguity_creates_required(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")

    result = await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )
    await db.commit()
    await db.refresh(inquiry)

    assert result.status == STATUS_REQUIRED
    assert result.version == 1
    assert review_blocks_convert(inquiry) is True
    assert inquiry.status == "review_required"
    assert inquiry.meta[REVIEW_KEY]["status"] == STATUS_REQUIRED
    assert len(inquiry.meta[REVIEW_KEY]["candidates"]) == 2
    assert inquiry.meta[REVIEW_KEY]["audit"]


@pytest.mark.asyncio
async def test_unique_match_does_not_create_required_review(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    account = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=suffix)

    result = await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        matched_client_account_id=str(account.id),
        own_company_id=own_company_id,
    )
    await db.commit()
    await db.refresh(inquiry)

    assert result.status == STATUS_NOT_REQUIRED
    assert review_blocks_convert(inquiry) is False
    assert inquiry.meta[REVIEW_KEY]["status"] == STATUS_NOT_REQUIRED

    with pytest.raises(AmbiguousMatchReviewError) as exc:
        await open_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
            candidates=[AmbiguityCandidateRef(client_account_id=str(account.id))],
            own_company_id=own_company_id,
        )
    assert exc.value.reason == "invalid_candidate"


@pytest.mark.asyncio
async def test_resolve_existing_client_account(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )

    resolved = await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="match_existing", client_account_id=str(a1.id)),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    await db.commit()
    await db.refresh(inquiry)

    assert resolved.status == STATUS_RESOLVED_MATCH
    assert resolved.review["decision"]["client_account_id"] == str(a1.id)
    assert review_blocks_convert(inquiry) is False
    assert inquiry.status == "open"


@pytest.mark.asyncio
async def test_resolve_create_new(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )

    resolved = await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="create_new"),
        expected_version=1,
        actor_id="actor-1",
        actor_role="admin",
        own_company_id=own_company_id,
    )
    await db.commit()
    assert resolved.status == STATUS_RESOLVED_CREATE_NEW
    assert resolved.convert_ready_ref["convert_allowed"] is True


@pytest.mark.asyncio
async def test_convert_blocked_until_review_resolved(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )

    with pytest.raises(ConvertMappingError) as blocked:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
        )
    assert blocked.value.reason == "unresolved_review"

    await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="create_new"),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )

    converted = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
    )
    await db.commit()
    assert converted.client_account_id
    assert converted.mapping["flights_ledger_id"] == ledger_id


@pytest.mark.asyncio
async def test_candidate_outside_evidence_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    outsider = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}x")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )
    with pytest.raises(AmbiguousMatchReviewError) as exc:
        await resolve_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
            decision=ReviewDecision(action="match_existing", client_account_id=str(outsider.id)),
            expected_version=1,
            actor_id="actor-1",
            actor_role="manager",
            own_company_id=own_company_id,
        )
    assert exc.value.reason == "candidate_outside_evidence"


@pytest.mark.asyncio
async def test_cross_tenant_candidate_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    foreign_id = account_crud.new_client_account_id()
    db.add(
        ClientAccount(
            id=foreign_id,
            tenant_id=str(uuid.uuid4()),
            own_company_id=str(uuid.uuid4()),
            display_name="Foreign",
            status="prospect",
        )
    )
    await db.flush()

    with pytest.raises(AmbiguousMatchReviewError) as exc:
        await open_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
            candidates=[
                AmbiguityCandidateRef(client_account_id=str(a1.id)),
                AmbiguityCandidateRef(client_account_id=foreign_id),
            ],
            own_company_id=own_company_id,
        )
    assert exc.value.reason == "cross_tenant_candidate"


@pytest.mark.asyncio
async def test_recruitment_destination_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(
        db,
        tenant_id=tenant_id,
        suffix=suffix,
        ledger_destination=DESTINATION_RECRUITMENT,
    )
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    with pytest.raises(AmbiguousMatchReviewError) as exc:
        await open_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_RECRUITMENT,
            flights_ledger_id=str(ledger_id),
            candidates=[
                AmbiguityCandidateRef(client_account_id=str(a1.id)),
                AmbiguityCandidateRef(client_account_id=str(a2.id)),
            ],
            own_company_id=own_company_id,
        )
    assert exc.value.reason == "recruitment_destination_rejected"


@pytest.mark.asyncio
async def test_repeat_same_decision_idempotent(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )
    first = await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="match_existing", client_account_id=str(a1.id)),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    second = await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="match_existing", client_account_id=str(a1.id)),
        expected_version=2,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    await db.commit()
    assert first.idempotent_replay is False
    assert second.idempotent_replay is True
    assert second.review == first.review


@pytest.mark.asyncio
async def test_conflicting_decision_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
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
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="match_existing", client_account_id=str(a1.id)),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    with pytest.raises(AmbiguousMatchReviewError) as exc:
        await resolve_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
            decision=ReviewDecision(action="create_new"),
            expected_version=2,
            actor_id="actor-1",
            actor_role="manager",
            own_company_id=own_company_id,
        )
    assert exc.value.reason == "conflicting_decision"


@pytest.mark.asyncio
async def test_stale_version_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )
    with pytest.raises(AmbiguousMatchReviewError) as exc:
        await resolve_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
            decision=ReviewDecision(action="create_new"),
            expected_version=99,
            actor_id="actor-1",
            actor_role="manager",
            own_company_id=own_company_id,
        )
    assert exc.value.reason == "stale_version"


@pytest.mark.asyncio
async def test_provenance_mismatch_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )
    with pytest.raises(AmbiguousMatchReviewError) as exc:
        await resolve_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(uuid.uuid4()),
            decision=ReviewDecision(action="create_new"),
            expected_version=1,
            actor_id="actor-1",
            actor_role="manager",
            own_company_id=own_company_id,
        )
    assert exc.value.reason in {"missing_flights_reference", "provenance_mismatch"}


@pytest.mark.asyncio
async def test_resolved_decision_immutable(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id, own_company_id = await _seed_inquiry(db, tenant_id=tenant_id, suffix=suffix)
    a1 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}a")
    a2 = await _client_account(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=f"{suffix}b")
    await open_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        candidates=[
            AmbiguityCandidateRef(client_account_id=str(a1.id)),
            AmbiguityCandidateRef(client_account_id=str(a2.id)),
        ],
        own_company_id=own_company_id,
    )
    first = await resolve_ambiguous_match_review(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="match_existing", client_account_id=str(a1.id)),
        expected_version=1,
        actor_id="actor-1",
        actor_role="manager",
        own_company_id=own_company_id,
    )
    frozen = dict(first.review)

    with pytest.raises(AmbiguousMatchReviewError) as reopen:
        await open_ambiguous_match_review(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
            candidates=[
                AmbiguityCandidateRef(client_account_id=str(a1.id)),
                AmbiguityCandidateRef(client_account_id=str(a2.id)),
            ],
            own_company_id=own_company_id,
        )
    assert reopen.value.reason == "resolved_immutable"

    await db.refresh(inquiry)
    assert inquiry.meta[REVIEW_KEY] == frozen
