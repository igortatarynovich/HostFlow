"""Stage 3E PR-2 — LeadCreated instrumentation via append_submission."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition import lead_activity as lead_activity_mod
from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    create_flight,
    transition_flight_status,
)
from backend.app.acquisition.lead_activity import lead_created_source_event_id
from backend.app.acquisition.submission_routing import (
    RoutingDecisionStatus,
    RoutingSource,
    UniversalRoutingDecision,
)
from backend.app.db.session import async_session_maker
from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy
from backend.app.intake_platform.submission_store import append_submission
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.tests.conftest import _init_data

_LEAD_ACTIVITY = Path(lead_activity_mod.__file__)


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


async def _seed_campaign_active_flight(db, *, tenant_id: str) -> tuple[Campaign, str]:
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


async def _seed_lead(
    db, *, tenant_id: str, own_company_id: str, created_at: datetime | None = None
) -> Lead:
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
    if created_at is not None:
        lead.created_at = created_at
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
        publication_id=None,
        invite_id=None,
        source={"channel": "public_intake"},
    )


def test_lead_activity_writes_only_via_append() -> None:
    src = _LEAD_ACTIVITY.read_text(encoding="utf-8")
    assert "append_activity_event" in src
    assert "AcquisitionActivityEvent(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "AcquisitionActivityEvent":
                raise AssertionError(f"raw construct at line {node.lineno}")


@pytest.mark.asyncio
async def test_append_submission_emits_lead_created() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    birth = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_active_flight(db, tenant_id=tenant_id)
        lead = await _seed_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=camp.own_company_id,
            created_at=birth,
        )
        routing = UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="sales_inquiry",
            campaign_id=camp.id,
            campaign_run_id=flight_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        ).to_dict()
        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=f"lead-created-{uuid4().hex}",
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            submission_id=str(entry["submission_id"]),
            event_types=["LeadCreated"],
        )
        assert len(rows) == 1
        ev = rows[0]
        assert ev.campaign_id == camp.id
        assert ev.flight_id == flight_id
        assert ev.submission_id == entry["submission_id"]
        assert ev.source_event_id == lead_created_source_event_id(lead.id)
        assert ev.payload == {
            "lead_id": lead.id,
            "submission_id": entry["submission_id"],
            "route_intent": "sales_inquiry",
        }
        assert "email" not in ev.payload
        assert ev.occurred_at == birth
        assert ev.recorded_at is not None
        assert ev.recorded_at > birth
        assert ev.provider is None
        await db.commit()


@pytest.mark.asyncio
async def test_reattach_same_lead_does_not_duplicate_lead_created() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_active_flight(db, tenant_id=tenant_id)
        lead = await _seed_lead(
            db, tenant_id=tenant_id, own_company_id=camp.own_company_id
        )
        routing = UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="sales_inquiry",
            campaign_id=camp.id,
            campaign_run_id=flight_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        ).to_dict()
        await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=f"lead-a-{uuid4().hex}",
        )
        await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "b@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=f"lead-b-{uuid4().hex}",
        )
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'LeadCreated' "
                "AND source_event_id = :s"
            ),
            {"t": tenant_id, "s": lead_created_source_event_id(lead.id)},
        )
        assert count.scalar() == 1
        await db.commit()


@pytest.mark.asyncio
async def test_non_acquisition_append_no_lead_created() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        oc = await _own_company_id(db, tenant_id)
        lead = await _seed_lead(db, tenant_id=tenant_id, own_company_id=oc)
        await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"entry": "questionnaire_invite"},
            idempotency_key=f"no-acq-lead-{uuid4().hex}",
        )
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'LeadCreated' "
                "AND source_event_id = :s"
            ),
            {"t": tenant_id, "s": lead_created_source_event_id(lead.id)},
        )
        assert count.scalar() == 0
        await db.commit()


@pytest.mark.asyncio
async def test_lead_created_rollback_drops_activity() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_active_flight(db, tenant_id=tenant_id)
        lead = await _seed_lead(
            db, tenant_id=tenant_id, own_company_id=camp.own_company_id
        )
        await db.commit()
        lead_id = lead.id
        campaign_id = camp.id

    async with async_session_maker() as db:
        routing = UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="sales_inquiry",
            campaign_id=campaign_id,
            campaign_run_id=flight_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        ).to_dict()
        await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead_id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=f"rb-lead-{uuid4().hex}",
        )
        await db.rollback()

    async with async_session_maker() as db:
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            event_types=["LeadCreated"],
        )
        assert rows == []
