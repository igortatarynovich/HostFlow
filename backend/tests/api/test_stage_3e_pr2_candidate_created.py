"""Stage 3E PR-2 — CandidateCreated instrumentation via lead conversion."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition import candidate_activity as candidate_activity_mod
from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.candidate_activity import (
    candidate_created_source_event_id,
    resolve_unique_submission_id,
)
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    create_flight,
    transition_flight_status,
)
from backend.app.acquisition.submission_routing import (
    RoutingDecisionStatus,
    RoutingSource,
    UniversalRoutingDecision,
    stamp_acquisition_routing_on_lead,
)
from backend.app.db.session import async_session_maker
from backend.app.intake_platform.constants import SUBMISSIONS_V1_KEY
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.app.modules.leads import lead_candidate_conversion as conversion_mod
from backend.app.modules.leads.lead_candidate_conversion import (
    create_candidate_from_lead_conversion,
)
from backend.tests.conftest import _init_data

_CAND_ACTIVITY = Path(candidate_activity_mod.__file__)
_CONVERSION = Path(conversion_mod.__file__)


async def _ensure_tenant(db, tenant_id: str) -> None:
    exists = (
        await db.execute(select(Tenant.id).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if exists is not None:
        return
    suffix = tenant_id.replace("-", "")[:8]
    db.add(
        Tenant(
            id=tenant_id,
            name=f"Tenant {suffix}",
            slug=f"t-{suffix}",
            api_key=f"api-{suffix}-{uuid4().hex[:8]}",
            is_active=True,
        )
    )
    await db.flush()


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name=f"OC {uuid4().hex[:6]}"))
        await db.flush()
    return str(oc)


async def _seed_campaign_flight(db, *, tenant_id: str) -> tuple[Campaign, str]:
    await _ensure_tenant(db, tenant_id)
    oc = await _own_company_id(db, tenant_id)
    campaign = Campaign(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        name=f"Campaign {uuid4().hex[:6]}",
        status="active",
        goal_type="hiring",
        primary_kpi="hires",
    )
    db.add(campaign)
    await db.flush()
    flight, _ = await create_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        actor_type=ACTOR_TYPE_SYSTEM,
    )
    await transition_flight_status(
        db,
        flight=flight,
        new_status=FLIGHT_STATUS_ACTIVE,
        actor_type=ACTOR_TYPE_SYSTEM,
    )
    campaign.current_flight_id = flight.id
    await db.flush()
    return campaign, flight.id


def _with_submission(lead: Lead, *, submission_id: str) -> None:
    normalized = dict(lead.normalized or {})
    normalized[SUBMISSIONS_V1_KEY] = [
        {"submission_id": submission_id, "schema_version": "submission_v1"}
    ]
    lead.normalized = normalized


async def _seed_lead(
    db,
    *,
    tenant_id: str,
    own_company_id: str,
    campaign_id: str | None = None,
    flight_id: str | None = None,
    submission_id: str | None = None,
    extra_submissions: list[str] | None = None,
) -> Lead:
    lead = Lead(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        status="new",
        source="public_intake",
        lead_type="candidate",
        payload={},
        normalized={},
    )
    db.add(lead)
    await db.flush()
    if campaign_id and flight_id:
        stamp_acquisition_routing_on_lead(
            lead,
            UniversalRoutingDecision(
                status=RoutingDecisionStatus.routed.value,
                route_intent="candidate_application",
                campaign_id=campaign_id,
                campaign_run_id=flight_id,
                source=RoutingSource.campaign_target.value,
                decided_at="2026-07-21T12:00:00+00:00",
            ),
        )
    if submission_id:
        _with_submission(lead, submission_id=submission_id)
        if extra_submissions:
            normalized = dict(lead.normalized or {})
            entries = list(normalized.get(SUBMISSIONS_V1_KEY) or [])
            for sid in extra_submissions:
                entries.append({"submission_id": sid})
            normalized[SUBMISSIONS_V1_KEY] = entries
            lead.normalized = normalized
    await db.flush()
    return lead


async def _fake_create_candidate_full(
    db,
    tenant_id: str,
    payload,
    *,
    actor_id=None,
    acl=None,
    source_lead=None,
):
    # Candidate.created_at column is TIMESTAMP WITHOUT TIME ZONE (naive UTC).
    birth = datetime(2026, 6, 15, 8, 0, 0)
    cand = Candidate(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=payload.get("own_company_id"),
        first_name=payload.get("first_name") or "A",
        last_name=payload.get("last_name") or "B",
        company_id=payload.get("company_id"),
        vacancy_id=payload.get("vacancy_id"),
        stage="new",
        status="new",
    )
    cand.created_at = birth
    db.add(cand)
    await db.flush()
    return cand


def test_candidate_activity_writes_only_via_append() -> None:
    src = _CAND_ACTIVITY.read_text(encoding="utf-8")
    assert "append_activity_event" in src
    assert "AcquisitionActivityEvent(" not in src


def test_conversion_emits_via_helper_not_raw_model() -> None:
    src = _CONVERSION.read_text(encoding="utf-8")
    assert "maybe_record_candidate_created_from_conversion" in src
    assert "AcquisitionActivityEvent(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "AcquisitionActivityEvent":
                raise AssertionError(f"raw construct at line {node.lineno}")


def test_resolve_unique_submission_id_requires_exactly_one() -> None:
    lead = Lead(
        id=str(uuid4()),
        tenant_id=str(uuid4()),
        payload={},
        normalized={SUBMISSIONS_V1_KEY: [{"submission_id": "s1"}, {"submission_id": "s2"}]},
    )
    assert resolve_unique_submission_id(lead) is None
    lead.normalized = {SUBMISSIONS_V1_KEY: [{"submission_id": "s1"}]}
    assert resolve_unique_submission_id(lead) == "s1"


@pytest.mark.asyncio
async def test_conversion_emits_candidate_created(monkeypatch) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    submission_id = str(uuid4())

    monkeypatch.setattr(
        conversion_mod, "create_candidate_full", _fake_create_candidate_full
    )
    monkeypatch.setattr(
        conversion_mod,
        "_emit_candidate_created_audit",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "backend.app.services.lead_communications.maybe_send_moving_forward_notice",
        AsyncMock(),
    )

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        lead = await _seed_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=camp.own_company_id,
            campaign_id=camp.id,
            flight_id=flight_id,
            submission_id=submission_id,
        )
        from backend.app.services.lead_rodo import mark_lead_rodo_source_provided
        mark_lead_rodo_source_provided(lead)
        cand = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload={
                "first_name": "A",
                "last_name": "B",
                "own_company_id": camp.own_company_id,
            },
            source_channel="public_intake",
            duplicate_match_level="none",
            conversion_reason="test",
        )
        assert lead.candidate_id == cand.id
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            submission_id=submission_id,
            event_types=["CandidateCreated"],
        )
        assert len(rows) == 1
        ev = rows[0]
        assert ev.source_event_id == candidate_created_source_event_id(cand.id)
        assert ev.payload == {
            "candidate_id": cand.id,
            "lead_id": lead.id,
            "submission_id": submission_id,
            "route_intent": "candidate_application",
        }
        assert ev.occurred_at == cand.created_at.replace(tzinfo=timezone.utc)
        assert ev.recorded_at is not None
        assert ev.recorded_at >= ev.occurred_at
        assert "email" not in ev.payload
        assert "creation_mode" not in ev.payload
        await db.commit()


@pytest.mark.asyncio
async def test_conversion_silent_without_stamp(monkeypatch) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    monkeypatch.setattr(
        conversion_mod, "create_candidate_full", _fake_create_candidate_full
    )
    monkeypatch.setattr(conversion_mod, "_emit_candidate_created_audit", AsyncMock())
    monkeypatch.setattr(
        "backend.app.services.lead_communications.maybe_send_moving_forward_notice",
        AsyncMock(),
    )

    async with async_session_maker() as db:
        oc = await _own_company_id(db, tenant_id)
        lead = await _seed_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=oc,
            submission_id=str(uuid4()),
        )
        from backend.app.services.lead_rodo import mark_lead_rodo_source_provided
        mark_lead_rodo_source_provided(lead)
        cand = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload={"first_name": "A", "last_name": "B", "own_company_id": oc},
            source_channel="meta",
            duplicate_match_level="none",
            conversion_reason="test",
        )
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'CandidateCreated' "
                "AND source_event_id = :s"
            ),
            {"t": tenant_id, "s": candidate_created_source_event_id(cand.id)},
        )
        assert count.scalar() == 0
        await db.commit()


@pytest.mark.asyncio
async def test_conversion_silent_when_submission_ambiguous(monkeypatch) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    monkeypatch.setattr(
        conversion_mod, "create_candidate_full", _fake_create_candidate_full
    )
    monkeypatch.setattr(conversion_mod, "_emit_candidate_created_audit", AsyncMock())
    monkeypatch.setattr(
        "backend.app.services.lead_communications.maybe_send_moving_forward_notice",
        AsyncMock(),
    )

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        lead = await _seed_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=camp.own_company_id,
            campaign_id=camp.id,
            flight_id=flight_id,
            submission_id=str(uuid4()),
            extra_submissions=[str(uuid4())],
        )
        from backend.app.services.lead_rodo import mark_lead_rodo_source_provided
        mark_lead_rodo_source_provided(lead)
        cand = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload={
                "first_name": "A",
                "last_name": "B",
                "own_company_id": camp.own_company_id,
            },
            source_channel="public_intake",
            duplicate_match_level="none",
            conversion_reason="test",
        )
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'CandidateCreated' "
                "AND source_event_id = :s"
            ),
            {"t": tenant_id, "s": candidate_created_source_event_id(cand.id)},
        )
        assert count.scalar() == 0
        await db.commit()


@pytest.mark.asyncio
async def test_idempotent_replay_no_candidate_created(monkeypatch) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    monkeypatch.setattr(conversion_mod, "_emit_candidate_created_audit", AsyncMock())
    monkeypatch.setattr(
        "backend.app.services.lead_context_carry.carry_lead_context_on_conversion",
        AsyncMock(),
    )

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        submission_id = str(uuid4())
        lead = await _seed_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=camp.own_company_id,
            campaign_id=camp.id,
            flight_id=flight_id,
            submission_id=submission_id,
        )
        cand = Candidate(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=camp.own_company_id,
            first_name="Existing",
            last_name="One",
            stage="new",
            status="new",
        )
        db.add(cand)
        await db.flush()
        lead.candidate_id = cand.id
        await db.flush()

        create_mock = AsyncMock(side_effect=AssertionError("must not insert"))
        monkeypatch.setattr(conversion_mod, "create_candidate_full", create_mock)

        from backend.app.services.lead_rodo import mark_lead_rodo_source_provided
        mark_lead_rodo_source_provided(lead)
        out = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload={"first_name": "X", "last_name": "Y"},
            source_channel="meta",
            duplicate_match_level="none",
            conversion_reason="replay",
        )
        assert out.id == cand.id
        create_mock.assert_not_called()
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'CandidateCreated'"
            ),
            {"t": tenant_id},
        )
        # Filter by candidate to avoid cross-test noise
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'CandidateCreated' "
                "AND source_event_id = :s"
            ),
            {"t": tenant_id, "s": candidate_created_source_event_id(cand.id)},
        )
        assert count.scalar() == 0
        await db.commit()


@pytest.mark.asyncio
async def test_rollback_after_link_drops_candidate_created(monkeypatch) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    submission_id = str(uuid4())
    monkeypatch.setattr(
        conversion_mod, "create_candidate_full", _fake_create_candidate_full
    )
    monkeypatch.setattr(conversion_mod, "_emit_candidate_created_audit", AsyncMock())
    monkeypatch.setattr(
        "backend.app.services.lead_communications.maybe_send_moving_forward_notice",
        AsyncMock(),
    )

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        lead = await _seed_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=camp.own_company_id,
            campaign_id=camp.id,
            flight_id=flight_id,
            submission_id=submission_id,
        )
        await db.commit()
        lead_id = lead.id
        campaign_id = camp.id

    async with async_session_maker() as db:
        lead = await db.get(Lead, lead_id)
        assert lead is not None
        from backend.app.services.lead_rodo import mark_lead_rodo_source_provided
        mark_lead_rodo_source_provided(lead)
        cand = await create_candidate_from_lead_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate_payload={
                "first_name": "A",
                "last_name": "B",
                "own_company_id": lead.own_company_id,
            },
            source_channel="public_intake",
            duplicate_match_level="none",
            conversion_reason="test",
        )
        source_key = candidate_created_source_event_id(cand.id)
        await db.rollback()

    async with async_session_maker() as db:
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'CandidateCreated' "
                "AND source_event_id = :s"
            ),
            {"t": tenant_id, "s": source_key},
        )
        assert count.scalar() == 0
        # campaign seed from first session remains; Activity must not.
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            event_types=["CandidateCreated"],
        )
        assert all(r.source_event_id != source_key for r in rows)
