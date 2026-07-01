"""Entity Profile Definition Registry P5B — Outcome Executor expansion."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text

from backend.app.entity_profile.decision_layer import (
    DecisionInput,
    IngestDisposition,
    OutcomeDecisionContext,
    evaluate_outcome_event_decision,
)
from backend.app.entity_profile.outcome_executor import execute_outcome_decision
from backend.app.models import Company, Lead
from backend.app.models.additional_service import ServiceOrder
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.own_company import OwnCompany
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.outcome_rules.reference import OutcomeEvent, OutcomeRuleType


async def _tenant_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        text("SELECT id FROM companies WHERE tenant_id = :tenant LIMIT 1"),
        {"tenant": tenant_id},
    )
    company_id = row.scalar_one_or_none()
    assert company_id, "test tenant must have a company"
    return str(company_id)


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
        db.add(OwnCompany(id=own_company_id, tenant_id=tenant_id, name=f"P5B OC {uuid.uuid4().hex[:6]}"))
        await db.flush()
    return str(own_company_id)


@pytest.mark.anyio
async def test_p5b_decision_create_client_on_won(db, tenant_id: str) -> None:
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="api",
        normalized={
            "ingest_envelope_v1": {"route_intent": RouteIntent.sales_inquiry.value},
            "company_name": "Acme Transport Sp. z o.o.",
            "email": "sales@acme.example",
        },
    )
    decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.won.value,
        ctx=OutcomeDecisionContext(client_company_name_present=True),
        email="sales@acme.example",
        phone="+48111222333",
    )
    assert decision.disposition == IngestDisposition.create_client.value
    assert decision.may_create_client is True
    assert OutcomeRuleType.create_client.value in [a.code for a in decision.outcome_resolution.actions]


@pytest.mark.anyio
async def test_p5b_decision_create_service_order_on_qualified(db, tenant_id: str) -> None:
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="csv_import",
        normalized={
            "ingest_envelope_v1": {"route_intent": RouteIntent.service_request.value},
            "full_name": "Service Contact",
        },
    )
    decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.qualified.value,
        ctx=OutcomeDecisionContext(service_company_resolved=True),
        email="service@example.com",
        phone="+48123456789",
    )
    assert decision.disposition == IngestDisposition.create_service_order.value
    assert decision.may_create_service_order is True
    assert OutcomeRuleType.create_service_order.value in [a.code for a in decision.outcome_resolution.actions]


@pytest.mark.anyio
async def test_p5b_executor_create_client_links_lead(db, tenant_id: str) -> None:
    await _tenant_company_id(db, tenant_id)
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={"contact": {"full_name": f"Contact {suffix}"}},
        normalized={
            "company_name": f"P5B Client {suffix}",
            "email": f"client-{suffix}@example.com",
            "phone": f"+48{uuid.uuid4().int % 10**9:09d}",
            "ingest_envelope_v1": {"route_intent": RouteIntent.sales_inquiry.value},
        },
        source="whatsapp",
        lead_type="client",
        lead_target_type="client_lead",
    )
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="whatsapp",
        normalized=dict(lead.normalized or {}),
    )
    decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.won.value,
        ctx=OutcomeDecisionContext(client_company_name_present=True),
        email=f"client-{suffix}@example.com",
        phone=lead.normalized.get("phone") if isinstance(lead.normalized, dict) else None,
    )
    normalized = dict(lead.normalized or {})
    result = await execute_outcome_decision(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=normalized,
        source="whatsapp",
        decision=decision,
    )
    assert result is not None
    assert result.entity_type == "client"
    assert result.idempotent_replay is False

    client = await db.get(Company, result.entity_id)
    assert client is not None
    assert lead.converted_client_id == result.entity_id
    assert lead.status == "processed"
    assert (lead.normalized or {}).get("converted_client_id") == result.entity_id


@pytest.mark.anyio
async def test_p5b_executor_create_service_order_links_lead(db, tenant_id: str) -> None:
    company_id = await _tenant_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=None,
        company_id=company_id,
        vacancy_id=None,
        payload={},
        normalized={
            "full_name": f"Service {suffix}",
            "email": f"svc-{suffix}@example.com",
            "ingest_envelope_v1": {"route_intent": RouteIntent.service_request.value},
        },
        source="public-form",
        lead_type="candidate",
        lead_target_type="service_order_lead",
    )
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="public-form",
        normalized=dict(lead.normalized or {}),
    )
    decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.qualified.value,
        ctx=OutcomeDecisionContext(service_company_resolved=True),
        email=f"svc-{suffix}@example.com",
    )
    normalized = dict(lead.normalized or {})
    result = await execute_outcome_decision(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=normalized,
        source="public-form",
        decision=decision,
    )
    assert result is not None
    assert result.entity_type == "service_order"
    assert result.idempotent_replay is False

    order = await db.get(ServiceOrder, result.entity_id)
    assert order is not None
    assert order.company_id == company_id
    assert (lead.normalized or {}).get("service_order_id") == result.entity_id
    assert lead.status == "processed"


@pytest.mark.anyio
async def test_p5b_idempotent_client_replay(db, tenant_id: str) -> None:
    await _tenant_company_id(db, tenant_id)
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized={
            "company_name": f"P5B Idem Client {suffix}",
            "email": f"idem-{suffix}@example.com",
            "ingest_envelope_v1": {"route_intent": RouteIntent.sales_inquiry.value},
        },
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="meta",
        normalized=dict(lead.normalized or {}),
    )
    ctx = OutcomeDecisionContext(client_company_name_present=True)
    decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.won.value,
        ctx=ctx,
        email=f"idem-{suffix}@example.com",
    )
    normalized = dict(lead.normalized or {})
    first = await execute_outcome_decision(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=normalized,
        source="meta",
        decision=decision,
    )
    assert first is not None
    await db.commit()

    replay_decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.won.value,
        ctx=OutcomeDecisionContext(
            client_company_name_present=True,
            existing_client_id=lead.converted_client_id,
        ),
        email=f"idem-{suffix}@example.com",
    )
    assert replay_decision.attach_client_id == first.entity_id
    second = await execute_outcome_decision(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=dict(lead.normalized or {}),
        source="meta",
        decision=replay_decision,
    )
    assert second is not None
    assert second.entity_id == first.entity_id
    assert second.idempotent_replay is True

    count = await db.scalar(
        select(func.count()).select_from(Company).where(
            Company.tenant_id == tenant_id,
            Company.name == f"P5B Idem Client {suffix}",
        )
    )
    assert int(count or 0) == 1


@pytest.mark.anyio
async def test_p5b_idempotent_service_order_replay(db, tenant_id: str) -> None:
    company_id = await _tenant_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=None,
        company_id=company_id,
        vacancy_id=None,
        payload={},
        normalized={
            "full_name": f"Idem Service {suffix}",
            "ingest_envelope_v1": {"route_intent": RouteIntent.service_request.value},
        },
        source="api",
        lead_type="candidate",
        lead_target_type="service_order_lead",
    )
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="api",
        normalized=dict(lead.normalized or {}),
    )
    decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.qualified.value,
        ctx=OutcomeDecisionContext(service_company_resolved=True),
    )
    normalized = dict(lead.normalized or {})
    first = await execute_outcome_decision(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=normalized,
        source="api",
        decision=decision,
    )
    assert first is not None
    await db.commit()

    replay_decision = await evaluate_outcome_event_decision(
        db,
        decision_input,
        outcome_event=OutcomeEvent.qualified.value,
        ctx=OutcomeDecisionContext(
            service_company_resolved=True,
            existing_service_order_id=(lead.normalized or {}).get("service_order_id"),
        ),
    )
    second = await execute_outcome_decision(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=dict(lead.normalized or {}),
        source="api",
        decision=replay_decision,
    )
    assert second is not None
    assert second.entity_id == first.entity_id
    assert second.idempotent_replay is True

    count = await db.scalar(
        select(func.count()).select_from(ServiceOrder).where(
            ServiceOrder.tenant_id == tenant_id,
            ServiceOrder.id == first.entity_id,
        )
    )
    assert int(count or 0) == 1


@pytest.mark.anyio
async def test_p5b_provider_agnostic_same_outcome(db, tenant_id: str) -> None:
    """Source channel is opaque — meta vs csv_import produce identical disposition."""
    base_normalized = {
        "ingest_envelope_v1": {"route_intent": RouteIntent.sales_inquiry.value},
        "company_name": "Provider Agnostic Co",
    }
    for source in ("meta", "csv_import", "telegram", "public-form"):
        decision_input = DecisionInput.from_normalized(
            tenant_id=tenant_id,
            source=source,
            normalized=base_normalized,
        )
        decision = await evaluate_outcome_event_decision(
            db,
            decision_input,
            outcome_event=OutcomeEvent.won.value,
            ctx=OutcomeDecisionContext(client_company_name_present=True),
            email="agnostic@example.com",
        )
        assert decision.disposition == IngestDisposition.create_client.value
        assert decision.may_create_client is True
