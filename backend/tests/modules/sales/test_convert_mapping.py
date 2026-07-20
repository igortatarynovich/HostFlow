"""ADR-022 Phase 2 — Convert mapping contract tests (Sales-only)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_SALES_INQUIRY,
    RESULT_SALES_INQUIRY,
)
from backend.app.acquisition.flights.destination_registry import DESTINATION_RECRUITMENT, DESTINATION_SALES
from backend.app.models import ClientAccount
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED, STATUS_PENDING, FlightDispatchLedger
from backend.app.models.own_company import OwnCompany
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.client_accounts.conversion import convert_client_lead
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.sales.services.ambiguous_match_review import mark_unique_match_not_required
from backend.app.modules.sales.services.convert_mapping import (
    CONVERT_MAPPING_KEY,
    ConvertMappingError,
    convert_sales_inquiry_mapping,
)
from backend.app.modules.sales.services.sales_inquiry_traceability import LINEAGE_KEY


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


async def _seed_inquiry_bundle(
    db,
    *,
    tenant_id: str,
    suffix: str,
    status: str = "received",
    review_required: bool = False,
    stamp_review: bool = True,
    ledger_destination: str = DESTINATION_SALES,
    ledger_status: str = STATUS_CONFIRMED,
    ledger_result_id: str | None = None,
    create_ledger: bool = True,
    normalized_extra: dict | None = None,
) -> tuple[SalesInquiry, str | None]:
    own_company_id = await _own_company_id(db, tenant_id)
    base_norm = {
        "company_name": f"Transport {suffix}",
        "email": f"client-{suffix}@example.com",
        "phone": f"+48{uuid.uuid4().int % 10**9:09d}",
        "full_name": f"Contact {suffix}",
        "need": {
            "industry": "logistics",
            "budget": "10k",
            "timeline": "Q3",
            "notes": f"Need note {suffix}",
        },
        "source_form_id": f"form-{suffix}",
    }
    if normalized_extra:
        base_norm.update(normalized_extra)

    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized=base_norm,
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )

    meta: dict = {
        "intake_result_v1": {
            "route_intent": "sales_inquiry",
            "destination": DESTINATION_SALES,
        }
    }
    if review_required:
        meta["review_required"] = True

    inquiry = SalesInquiry(
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        status=status,
        source="public_intake",
        own_company_id=own_company_id,
        form_id=f"form-{suffix}",
        meta=meta,
        notes=None,
    )
    db.add(inquiry)
    await db.flush()

    ledger_id: str | None = None
    if create_ledger:
        ledger_id = str(uuid.uuid4())
        result_id = ledger_result_id if ledger_result_id is not None else str(inquiry.id)
        db.add(
            FlightDispatchLedger(
                id=ledger_id,
                tenant_id=tenant_id,
                idempotency_key=f"flights.dispatch:{tenant_id}:{lead.id}:sales_inquiry:{suffix}",
                transport_lead_id=str(lead.id),
                route_intent="sales_inquiry",
                destination=ledger_destination,
                dispatcher_id=DISPATCHER_SALES_INQUIRY,
                status=ledger_status,
                module_owner=ledger_destination if ledger_destination == DESTINATION_SALES else "recruitment",
                result_type=RESULT_SALES_INQUIRY if ledger_destination == DESTINATION_SALES else "application",
                result_id=result_id,
                confirmed_at=datetime.now(timezone.utc) if ledger_status == STATUS_CONFIRMED else None,
            )
        )
        await db.flush()
        # Convert requires an explicit Review stamp (not_required / resolved_*).
        if (
            stamp_review
            and not review_required
            and status not in {"rejected", "closed", "abandoned", "review_required"}
            and ledger_destination == DESTINATION_SALES
            and ledger_status == STATUS_CONFIRMED
        ):
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

    return inquiry, ledger_id


@pytest.mark.asyncio
async def test_successful_convert_mapping(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(db, tenant_id=tenant_id, suffix=suffix)
    assert ledger_id is not None

    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        actor_id="actor-1",
    )
    await db.commit()

    assert result.idempotent_replay is False
    assert result.destination == DESTINATION_SALES
    assert result.flights_ledger_id == ledger_id
    assert result.client_account_id
    assert result.mapping["version"] == 1
    assert result.mapping["questionnaire_projections"]["industry"] == "logistics"
    assert result.mapping["questionnaire_projections"]["budget"] == "10k"
    assert result.mapping["questionnaire_projections"]["source_form_id"] == f"form-{suffix}"
    assert result.traceability_refs["sales_inquiry_id"] == str(inquiry.id)
    assert result.traceability_refs["flights_ledger_id"] == ledger_id
    assert result.traceability_refs["client_account_id"] == result.client_account_id

    await db.refresh(inquiry)
    assert inquiry.status == "converted"
    assert inquiry.meta[CONVERT_MAPPING_KEY]["client_account_id"] == result.client_account_id


@pytest.mark.asyncio
async def test_missing_destination(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(db, tenant_id=tenant_id, suffix=suffix)
    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination="",
            flights_ledger_id=str(ledger_id),
        )
    assert exc.value.reason == "missing_destination"


@pytest.mark.asyncio
async def test_match_existing_review_decision_is_applied(db, tenant_id: str) -> None:
    from backend.app.modules.sales.services.ambiguous_match_review import (
        AmbiguityCandidateRef,
        ReviewDecision,
        open_ambiguous_match_review,
        resolve_ambiguous_match_review,
    )

    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(db, tenant_id=tenant_id, suffix=suffix)
    own_company_id = str(inquiry.own_company_id)
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
        flights_ledger_id=str(ledger_id),
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
        flights_ledger_id=str(ledger_id),
        decision=ReviewDecision(action="match_existing", client_account_id=str(existing.id)),
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
        flights_ledger_id=str(ledger_id),
        actor_id="actor-1",
    )
    await db.commit()

    assert result.client_account_id == str(existing.id)
    assert result.mapping["review_decision"]["action"] == "match_existing"
    created = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == str(inquiry.lead_id))
    )
    assert created == 0


@pytest.mark.asyncio
async def test_unresolved_review_blocks_convert(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(
        db,
        tenant_id=tenant_id,
        suffix=suffix,
        status="review_required",
        review_required=True,
    )
    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
        )
    assert exc.value.reason == "unresolved_review"


@pytest.mark.asyncio
async def test_duplicate_and_repeated_convert_are_idempotent(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(db, tenant_id=tenant_id, suffix=suffix)

    first = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
    )
    await db.commit()
    mapping_first = dict(first.mapping)

    second = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
    )
    await db.commit()

    third = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
    )
    await db.commit()

    assert second.idempotent_replay is True
    assert third.idempotent_replay is True
    assert first.client_account_id == second.client_account_id == third.client_account_id
    assert second.mapping == mapping_first
    assert third.mapping == mapping_first

    account_count = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == str(inquiry.lead_id))
    )
    assert account_count == 1


@pytest.mark.asyncio
async def test_invalid_inquiry_state(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(
        db,
        tenant_id=tenant_id,
        suffix=suffix,
        status="rejected",
    )
    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
        )
    assert exc.value.reason == "invalid_inquiry_state"


@pytest.mark.asyncio
async def test_recruitment_destination_rejected(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(
        db,
        tenant_id=tenant_id,
        suffix=suffix,
        ledger_destination=DESTINATION_RECRUITMENT,
    )
    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_RECRUITMENT,
            flights_ledger_id=str(ledger_id),
        )
    assert exc.value.reason == "recruitment_destination_rejected"


@pytest.mark.asyncio
async def test_missing_flights_reference(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, _ = await _seed_inquiry_bundle(
        db,
        tenant_id=tenant_id,
        suffix=suffix,
        create_ledger=False,
    )
    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id="",
        )
    assert exc.value.reason == "missing_flights_reference"


@pytest.mark.asyncio
async def test_unconfirmed_flights_reference(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(
        db,
        tenant_id=tenant_id,
        suffix=suffix,
        ledger_status=STATUS_PENDING,
    )
    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
        )
    assert exc.value.reason == "unconfirmed_flights_reference"


@pytest.mark.asyncio
async def test_immutable_mapping_after_convert(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(db, tenant_id=tenant_id, suffix=suffix)

    result = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        actor_id="actor-a",
    )
    await db.commit()
    frozen = dict(result.mapping)

    # Mutate transport questionnaire fields after convert — replay must keep original mapping.
    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(inquiry.lead_id))
    assert locked is not None
    norm = dict(locked.normalized or {})
    norm["need"] = {"industry": "hacked", "budget": "999", "notes": "should-not-appear"}
    locked.normalized = norm
    await db.flush()

    replay = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
        actor_id="actor-b",
    )
    await db.commit()

    assert replay.idempotent_replay is True
    assert replay.mapping == frozen
    assert replay.mapping["questionnaire_projections"]["industry"] == "logistics"
    assert replay.mapping.get("converted_by") == "actor-a"


@pytest.mark.asyncio
async def test_legacy_convert_then_mapping_replay_is_stable(db, tenant_id: str) -> None:
    """If ClientAccount already exists via legacy convert, mapping stamps once and replays."""
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(db, tenant_id=tenant_id, suffix=suffix)
    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(inquiry.lead_id))
    assert locked is not None
    legacy = await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
    await db.flush()

    mapped = await convert_sales_inquiry_mapping(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=str(ledger_id),
    )
    await db.commit()
    assert mapped.client_account_id == str(legacy.client_account.id)
    assert mapped.mapping["client_account_id"] == str(legacy.client_account.id)
    assert mapped.mapping["flights_ledger_id"] == ledger_id


@pytest.mark.asyncio
async def test_missing_review_decision_fails_closed(db, tenant_id: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(
        db,
        tenant_id=tenant_id,
        suffix=suffix,
        stamp_review=False,
    )
    inquiry_id = str(inquiry.id)
    await db.commit()
    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=inquiry_id,
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
        )
    assert exc.value.reason == "missing_review_decision"
    await db.rollback()
    reloaded = await db.get(SalesInquiry, inquiry_id)
    assert reloaded is not None
    assert reloaded.status != "converted"
    assert CONVERT_MAPPING_KEY not in (reloaded.meta or {})


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_convert_unit(db, tenant_id: str, monkeypatch) -> None:
    """Audit is mandatory: failure must leave no ClientAccount / mapping / lineage / lead bind."""
    suffix = uuid.uuid4().hex[:8]
    inquiry, ledger_id = await _seed_inquiry_bundle(db, tenant_id=tenant_id, suffix=suffix)
    inquiry_id = str(inquiry.id)
    lead_id = str(inquiry.lead_id)
    await db.commit()

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("forced audit failure")

    monkeypatch.setattr(
        "backend.app.modules.sales.services.convert_mapping.log_activity",
        _boom,
    )

    with pytest.raises(ConvertMappingError) as exc:
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=inquiry_id,
            destination=DESTINATION_SALES,
            flights_ledger_id=str(ledger_id),
            actor_id=None,
        )
    assert exc.value.reason == "audit_write_failed"
    await db.rollback()

    reloaded = await db.get(SalesInquiry, inquiry_id)
    assert reloaded is not None
    assert reloaded.status != "converted"
    assert CONVERT_MAPPING_KEY not in (reloaded.meta or {})
    assert LINEAGE_KEY not in (reloaded.meta or {})

    lead = await leads_crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    assert lead is not None
    assert not getattr(lead, "client_account_id", None)

    account_count = await db.scalar(
        select(func.count())
        .select_from(ClientAccount)
        .where(ClientAccount.source_lead_id == lead_id)
    )
    assert account_count == 0
