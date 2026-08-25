"""Stage 3E PR-2 — SubmissionReceived instrumentation."""

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
from backend.app.acquisition.submission_activity import (
    submission_received_source_event_id,
)
from backend.app.acquisition.submission_routing import (
    RoutingDecisionStatus,
    RoutingSource,
    UniversalRoutingDecision,
)
from backend.app.db.session import async_session_maker
from backend.app.acquisition import submission_activity as submission_activity_mod
from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy
from backend.app.intake_platform.submission_store import append_submission
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.tests.conftest import _init_data

_SUBMISSION_ACTIVITY = Path(submission_activity_mod.__file__)


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


def _policy(*, form_id: str | None = None) -> EffectivePolicy:
    return EffectivePolicy(
        purpose="inquiry",
        target_entity_profile_code="sales_inquiry",
        submission_policy=SubmissionPolicy.from_dict({"mode": "create"}),
        form_id=form_id or str(uuid4()),
        published_version=1,
        publication_id=None,
        invite_id=None,
        source={"channel": "public_intake"},
    )


def test_submission_activity_writes_only_via_append() -> None:
    src = _SUBMISSION_ACTIVITY.read_text(encoding="utf-8")
    assert "append_activity_event" in src
    assert "AcquisitionActivityEvent(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "AcquisitionActivityEvent":
                raise AssertionError(f"raw construct at line {node.lineno}")


@pytest.mark.asyncio
async def test_append_submission_with_routing_emits_submission_received() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_active_flight(db, tenant_id=tenant_id)
        lead = await _seed_lead(
            db, tenant_id=tenant_id, own_company_id=camp.own_company_id
        )
        form_id = str(uuid4())
        routing = UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="sales_inquiry",
            campaign_id=camp.id,
            campaign_run_id=flight_id,
            form_id=form_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        ).to_dict()

        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(form_id=form_id),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=f"sub-recv-{uuid4().hex}",
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=str(entry["submission_id"]),
            event_types=["SubmissionReceived"],
        )
        assert len(rows) == 1
        ev = rows[0]
        assert ev.campaign_id == camp.id
        assert ev.flight_id == flight_id
        assert ev.submission_id == entry["submission_id"]
        assert ev.endpoint_id == f"form:{form_id}"
        assert ev.source_event_id == submission_received_source_event_id(
            entry["submission_id"]
        )
        assert ev.payload.get("normalized_schema_version") == "submission_v1"
        assert ev.provider is None
        await db.commit()


@pytest.mark.asyncio
async def test_idempotent_append_returns_same_submission_received() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    key = f"idem-{uuid4().hex}"

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
        first = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=key,
        )
        second = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "b@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=key,
        )
        assert first["submission_id"] == second["submission_id"]
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'SubmissionReceived' "
                "AND submission_id = :s"
            ),
            {"t": tenant_id, "s": first["submission_id"]},
        )
        assert count.scalar() == 1
        await db.commit()


@pytest.mark.asyncio
async def test_rollback_drops_submission_received() -> None:
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
        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead_id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"acquisition_routing_v1": routing},
            idempotency_key=f"rb-{uuid4().hex}",
        )
        submission_id = entry["submission_id"]
        await db.rollback()

    async with async_session_maker() as db:
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=submission_id,
            event_types=["SubmissionReceived"],
        )
        assert rows == []


@pytest.mark.asyncio
async def test_non_acquisition_append_emits_nothing() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        oc = await _own_company_id(db, tenant_id)
        lead = await _seed_lead(db, tenant_id=tenant_id, own_company_id=oc)
        entry = await append_submission(
            db,
            tenant_id=tenant_id,
            lead_id=lead.id,
            effective_policy=_policy(),
            normalized_values={"email": "a@example.com"},
            entry_context={"entry": "questionnaire_invite"},
            idempotency_key=f"no-acq-{uuid4().hex}",
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=str(entry["submission_id"]),
        )
        assert rows == []
        await db.commit()
