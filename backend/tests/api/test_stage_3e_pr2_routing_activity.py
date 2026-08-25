"""Stage 3E PR-2 — RoutingCompleted / RoutingFailed instrumentation."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    create_flight,
    transition_flight_status,
)
from backend.app.acquisition.submission_routing import (
    RoutingDecisionStatus,
    RoutingSource,
    UnresolvedReason,
    UniversalRoutingDecision,
    maybe_record_routing_activity_from_entry_context,
    record_routing_activity_for_submission,
    routing_activity_source_event_id,
)
from backend.app.acquisition import submission_routing as routing_mod
from backend.app.db.session import async_session_maker
from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy
from backend.app.intake_platform.submission_store import append_submission
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign, CampaignTarget
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.tests.conftest import _init_data

_ROUTING_PATH = Path(routing_mod.__file__)


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


async def _seed_campaign_flight_target(
    db, *, tenant_id: str
) -> tuple[Campaign, str, str]:
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
    target = CampaignTarget(
        id=str(uuid4()),
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        target_type="vacancy",
        target_id=str(uuid4()),
        target_module="recruitment",
        route_intent="candidate_application",
        role="primary",
        sort_order=0,
    )
    db.add(target)
    await db.flush()
    return campaign, flight.id, target.id


async def _seed_lead(db, *, tenant_id: str, own_company_id: str) -> Lead:
    lead = Lead(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        status="new",
        source="public_intake",
        lead_type="client",
        payload={},
        normalized={},
    )
    db.add(lead)
    await db.flush()
    return lead


def _policy() -> EffectivePolicy:
    return EffectivePolicy(
        purpose="inquiry",
        target_entity_profile_code="sales_inquiry",
        submission_policy=SubmissionPolicy.from_dict({"mode": "create"}),
        form_id=str(uuid4()),
        published_version=1,
        source={"channel": "public_intake"},
    )


def test_routing_activity_writes_only_via_append() -> None:
    src = _ROUTING_PATH.read_text(encoding="utf-8")
    assert "append_activity_event" in src
    assert "AcquisitionActivityEvent(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "AcquisitionActivityEvent":
                raise AssertionError(f"raw construct at line {node.lineno}")


@pytest.mark.asyncio
async def test_routing_completed_after_successful_routed_append() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id, target_id = await _seed_campaign_flight_target(
            db, tenant_id=tenant_id
        )
        lead = await _seed_lead(
            db, tenant_id=tenant_id, own_company_id=camp.own_company_id
        )
        decision = UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="candidate_application",
            campaign_id=camp.id,
            campaign_run_id=flight_id,
            campaign_target_id=target_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        )
        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": decision.to_dict()},
            idempotency_key=f"rt-ok-{uuid4().hex}",
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=str(entry["submission_id"]),
            event_types=["RoutingCompleted"],
        )
        assert len(rows) == 1
        ev = rows[0]
        assert ev.campaign_id == camp.id
        assert ev.flight_id == flight_id
        assert ev.submission_id == entry["submission_id"]
        assert ev.payload["route_intent"] == "candidate_application"
        assert ev.payload["routing_source"] == "campaign_target"
        assert ev.payload["campaign_target_id"] == target_id
        assert ev.payload["target_type"] == "vacancy"
        assert "stack" not in str(ev.payload).lower()
        assert ev.source_event_id == routing_activity_source_event_id(
            event_type="RoutingCompleted", submission_id=entry["submission_id"]
        )
        await db.commit()


@pytest.mark.asyncio
async def test_routing_failed_for_handled_unresolved_with_campaign() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id, _target_id = await _seed_campaign_flight_target(
            db, tenant_id=tenant_id
        )
        lead = await _seed_lead(
            db, tenant_id=tenant_id, own_company_id=camp.own_company_id
        )
        decision = UniversalRoutingDecision(
            status=RoutingDecisionStatus.unresolved.value,
            route_intent="unknown",
            campaign_id=camp.id,
            campaign_run_id=flight_id,
            unresolved_reason=UnresolvedReason.missing_primary_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        )
        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": decision.to_dict()},
            idempotency_key=f"rt-fail-{uuid4().hex}",
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=str(entry["submission_id"]),
            event_types=["RoutingFailed", "RoutingCompleted"],
        )
        assert [r.event_type for r in rows] == ["RoutingFailed"]
        assert rows[0].payload["reason_code"] == "missing_primary_target"
        assert rows[0].payload["route_intent"] == "unknown"
        await db.commit()


@pytest.mark.asyncio
async def test_routing_without_campaign_emits_nothing() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        oc = await _own_company_id(db, tenant_id)
        lead = await _seed_lead(db, tenant_id=tenant_id, own_company_id=oc)
        decision = UniversalRoutingDecision(
            status=RoutingDecisionStatus.unresolved.value,
            route_intent="unknown",
            unresolved_reason=UnresolvedReason.no_intake_context.value,
            decided_at="2026-07-21T12:00:00+00:00",
        )
        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": decision.to_dict()},
            idempotency_key=f"rt-nocamp-{uuid4().hex}",
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=str(entry["submission_id"]),
            event_types=["RoutingCompleted", "RoutingFailed"],
        )
        assert rows == []
        await db.commit()


@pytest.mark.asyncio
async def test_routing_retry_returns_same_event() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id, target_id = await _seed_campaign_flight_target(
            db, tenant_id=tenant_id
        )
        submission_id = str(uuid4())
        decision = UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="sales_inquiry",
            campaign_id=camp.id,
            campaign_run_id=flight_id,
            campaign_target_id=target_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        )
        first = await record_routing_activity_for_submission(
            db,
            tenant_id=tenant_id,
            decision=decision,
            submission_id=submission_id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        second = await record_routing_activity_for_submission(
            db,
            tenant_id=tenant_id,
            decision=decision,
            submission_id=submission_id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        assert first is not None and second is not None
        assert first.id == second.id
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND submission_id = :s "
                "AND event_type = 'RoutingCompleted'"
            ),
            {"t": tenant_id, "s": submission_id},
        )
        assert count.scalar() == 1
        await db.commit()


@pytest.mark.asyncio
async def test_routing_rollback_emits_zero_events() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id, target_id = await _seed_campaign_flight_target(
            db, tenant_id=tenant_id
        )
        lead = await _seed_lead(
            db, tenant_id=tenant_id, own_company_id=camp.own_company_id
        )
        await db.commit()
        lead_id = lead.id
        campaign_id = camp.id

    async with async_session_maker() as db:
        decision = UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="sales_inquiry",
            campaign_id=campaign_id,
            campaign_run_id=flight_id,
            campaign_target_id=target_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        )
        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead_id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": decision.to_dict()},
            idempotency_key=f"rt-rb-{uuid4().hex}",
        )
        submission_id = entry["submission_id"]
        await db.rollback()

    async with async_session_maker() as db:
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=submission_id,
            event_types=["RoutingCompleted", "RoutingFailed", "SubmissionReceived"],
        )
        assert rows == []


@pytest.mark.asyncio
async def test_entry_context_hook_skips_without_submission_id() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id, _ = await _seed_campaign_flight_target(
            db, tenant_id=tenant_id
        )
        out = await maybe_record_routing_activity_from_entry_context(
            db,
            tenant_id=tenant_id,
            submission_entry={},
            entry_context={
                "acquisition_routing_v1": {
                    "status": "routed",
                    "campaign_id": camp.id,
                    "campaign_run_id": flight_id,
                    "route_intent": "sales_inquiry",
                }
            },
        )
        assert out is None
        await db.commit()
