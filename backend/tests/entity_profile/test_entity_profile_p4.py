"""Entity Profile Definition Registry P4 — Decision Layer bridge."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.decision_layer import (
    DecisionInput,
    IngestDecisionContext,
    IngestDisposition,
    evaluate_ingest_decision,
)
from backend.app.entity_profile.reverse_map import (
    STATIC_LEGACY_CANDIDATE_PROFILE_TO_ENTITY,
    find_entity_profile_code_by_legacy_candidate_code,
)
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.vacancy_bridge import resolve_entity_profile_hints_from_vacancy
from backend.app.models import Candidate, Lead
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.vacancy import Vacancy
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.outcome_rules.reference import OutcomeRuleType
from backend.tests.modules.leads.conftest import post_meta_lead


async def _tenant_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        text("SELECT id FROM companies WHERE tenant_id = :tenant LIMIT 1"),
        {"tenant": tenant_id},
    )
    company_id = row.scalar_one_or_none()
    assert company_id, "test tenant must have a company"
    return str(company_id)


def _meta_payload(*, form_id: str, phone: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": str(uuid.uuid4().int)[:15],
                            "form_id": form_id,
                            "field_data": [
                                {"name": "phone_number", "values": [phone]},
                                {"name": "first_name", "values": ["Jan"]},
                            ],
                        }
                    }
                ]
            }
        ]
    }


def test_p4_decision_input_from_ingest_envelope() -> None:
    normalized = {
        "ingest_envelope_v1": {
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "route_intent": RouteIntent.candidate_application.value,
        },
        "email": "driver@example.com",
    }
    decision_input = DecisionInput.from_normalized(
        tenant_id="11111111-1111-1111-1111-111111111111",
        source="meta",
        normalized=normalized,
    )
    assert decision_input.entity_profile_code == DRIVER_CE_PROFILE_CODE
    assert decision_input.route_intent == RouteIntent.candidate_application.value
    payload = decision_input.to_dict()
    assert payload["entity_profile_code"] == DRIVER_CE_PROFILE_CODE


@pytest.mark.anyio
async def test_p4_lead_only_sales_route(db, tenant_id: str) -> None:
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="meta",
        normalized={
            "ingest_envelope_v1": {"route_intent": RouteIntent.sales_inquiry.value},
        },
    )
    decision = await evaluate_ingest_decision(
        db,
        decision_input,
        ctx=IngestDecisionContext(sales_lead_without_candidate=True),
        email="sales@example.com",
        phone="+48111222333",
    )
    assert decision.disposition == IngestDisposition.lead_only.value
    assert decision.may_create_candidate is False
    assert OutcomeRuleType.none.value in [a.code for a in decision.outcome_resolution.actions]


@pytest.mark.anyio
async def test_p4_create_candidate_disposition(db, tenant_id: str) -> None:
    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="meta",
        normalized={
            "ingest_envelope_v1": {
                "route_intent": RouteIntent.candidate_application.value,
                "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            }
        },
    )
    decision = await evaluate_ingest_decision(
        db,
        decision_input,
        ctx=IngestDecisionContext(
            may_auto_convert=True,
            triage_gate_bypass=True,
            vacancy_resolved=True,
            effective_processing_mode="automatic",
            auto_create_enabled=True,
        ),
        email=f"new-{uuid.uuid4().hex[:8]}@example.com",
        phone=f"+48{uuid.uuid4().int % 10**9:09d}",
    )
    assert decision.disposition == IngestDisposition.create_candidate.value
    assert decision.may_create_candidate is True
    assert OutcomeRuleType.create_candidate.value in [a.code for a in decision.outcome_resolution.actions]


@pytest.mark.anyio
async def test_p4_blocked_duplicate_disposition(db, tenant_id: str) -> None:
    company_id = await _tenant_company_id(db, tenant_id)
    phone = f"+48{uuid.uuid4().int % 10**9:09d}"
    existing = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id,
        first_name="Existing",
        last_name="Driver",
        phone=phone,
        source="manual",
    )
    db.add(existing)
    await db.commit()

    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="meta",
        normalized={
            "ingest_envelope_v1": {
                "route_intent": RouteIntent.candidate_application.value,
                "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            }
        },
        company_id=company_id,
    )
    decision = await evaluate_ingest_decision(
        db,
        decision_input,
        ctx=IngestDecisionContext(
            may_auto_convert=True,
            triage_gate_bypass=True,
            vacancy_resolved=True,
        ),
        email=None,
        phone=phone,
    )
    assert decision.disposition == IngestDisposition.blocked_duplicate.value
    assert decision.may_create_candidate is False
    assert decision.attach_candidate_id == str(existing.id)


@pytest.mark.anyio
async def test_p4_reverse_map_expansion_static() -> None:
    assert STATIC_LEGACY_CANDIDATE_PROFILE_TO_ENTITY["poltrakt_drivers"] == DRIVER_CE_PROFILE_CODE
    assert STATIC_LEGACY_CANDIDATE_PROFILE_TO_ENTITY["base"] == DRIVER_CE_PROFILE_CODE


@pytest.mark.anyio
async def test_p4_reverse_map_poltrakt_drivers(db, tenant_id: str) -> None:
    mapped = await find_entity_profile_code_by_legacy_candidate_code(
        db,
        tenant_id=tenant_id,
        legacy_candidate_profile_code="poltrakt_drivers",
    )
    assert mapped == DRIVER_CE_PROFILE_CODE


@pytest.mark.anyio
async def test_p4_vacancy_derived_entity_profile(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile

    company_id = await _tenant_company_id(db, tenant_id)
    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await ensure_driver_ce_default_profile(db, tenant_id)

    profile = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.code == "driver_ce_default",
            )
        )
    ).scalar_one_or_none()
    assert profile is not None

    vacancy = Vacancy(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id,
        title=f"P4 vacancy {uuid.uuid4().hex[:6]}",
        candidate_profile_id=profile.id,
    )
    db.add(vacancy)
    await db.commit()

    entity_code, profile_id, legacy_code = await resolve_entity_profile_hints_from_vacancy(
        db,
        tenant_id=tenant_id,
        vacancy_id=vacancy.id,
    )
    assert legacy_code == "driver_ce_default"
    assert profile_id == profile.id
    assert entity_code == DRIVER_CE_PROFILE_CODE


@pytest.mark.anyio
async def test_p4_meta_ingest_stamps_decision_result(client, manager_headers, tenant_id: str) -> None:
    try:
        from backend.app.db.session import async_session_maker

        async with async_session_maker() as session:
            await session.execute(text("SELECT entity_profile_code FROM intake_source_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"P2 intake binding not available: {exc}")

    from backend.app.models.own_company import OwnCompany

    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        oc = OwnCompany(id=str(uuid.uuid4()), tenant_id=tenant_id, name=f"P4 decision {uuid.uuid4().hex[:6]}")
        session.add(oc)
        await session.flush()
        form_id = f"form-{uuid.uuid4().hex[:8]}"
        intake_profile = await intake_crud.create_profile(
            session,
            tenant_id=tenant_id,
            code=f"meta-p4-{uuid.uuid4().hex[:6]}",
            name="Meta P4 decision",
            own_company_id=oc.id,
            provider="meta",
            channel="paid",
            route_intent=RouteIntent.candidate_application.value,
            entity_profile_code=DRIVER_CE_PROFILE_CODE,
        )
        await intake_crud.create_binding(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=intake_profile.id,
            provider="meta",
            external_key=f"form_id:{form_id}",
            external_key_secondary="",
        )
        await session.commit()

    phone = f"+48{uuid.uuid4().int % 10**9:09d}"
    resp = await post_meta_lead(client, manager_headers, _meta_payload(form_id=form_id, phone=phone))
    assert resp.status_code in (200, 201), resp.text
    lead_id = resp.json().get("lead_id")
    assert lead_id

    async with async_session_maker() as session:
        lead = (await session.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
        assert lead is not None
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        assert norm.get("decision_input_v1", {}).get("entity_profile_code") == DRIVER_CE_PROFILE_CODE
        decision = norm.get("decision_result_v1") or {}
        assert decision.get("entity_profile_code") == DRIVER_CE_PROFILE_CODE
        assert decision.get("disposition") in {
            IngestDisposition.create_candidate.value,
            IngestDisposition.needs_routing.value,
            IngestDisposition.lead_only.value,
        }


@pytest.mark.anyio
async def test_p4_duplicate_meta_ingest_no_new_candidate(db, tenant_id: str) -> None:
    """Integration: duplicate match blocks Candidate INSERT via Decision Layer."""
    company_id = await _tenant_company_id(db, tenant_id)
    phone = f"+48{uuid.uuid4().int % 10**9:09d}"
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"

    existing = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id,
        first_name="Dup",
        last_name="Driver",
        phone=phone,
        email=email,
        source="manual",
    )
    db.add(existing)
    await db.commit()

    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source="meta",
        normalized={
            "ingest_envelope_v1": {
                "route_intent": RouteIntent.candidate_application.value,
                "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            },
            "email": email,
            "phone": phone,
        },
        company_id=company_id,
    )
    decision = await evaluate_ingest_decision(
        db,
        decision_input,
        ctx=IngestDecisionContext(
            may_auto_convert=True,
            triage_gate_bypass=True,
            vacancy_resolved=True,
        ),
        email=email,
        phone=phone,
    )
    assert decision.disposition == IngestDisposition.blocked_duplicate.value
    assert decision.may_create_candidate is False
    assert decision.attach_candidate_id == str(existing.id)
