"""Open-queue lead vs lead exact duplicate (email/phone) before a candidate exists."""

from __future__ import annotations

import uuid

import pytest

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.decision_layer import (
    DecisionInput,
    IngestDecisionContext,
    IngestDisposition,
    evaluate_ingest_decision,
)
from backend.app.models.lead import Lead
from backend.app.modules.leads.duplicate_resolution import resolve_lead_duplicate_match
from backend.tests.conftest import _set_tenant


def _open_lead(*, tenant_id: str, email: str, phone: str, external_id: str) -> Lead:
    return Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        lead_type="candidate",
        lead_target_type="candidate",
        source="meta",
        status="needs_routing",
        external_id=external_id,
        payload={"id": external_id},
        normalized={"email": email, "phone": phone, "full_name": "Walery Famicki"},
    )


@pytest.mark.anyio
async def test_resolve_match_finds_prior_open_lead_by_email(tenant_id: str) -> None:
    email = f"open-dup-{uuid.uuid4().hex[:10]}@example.com"
    phone = "+48570519008"
    first = _open_lead(tenant_id=tenant_id, email=email, phone=phone, external_id="lg-a")
    second = _open_lead(tenant_id=tenant_id, email=email, phone=phone, external_id="lg-b")
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        session.add_all([first, second])
        await session.commit()

        match = await resolve_lead_duplicate_match(
            session,
            tenant_id=tenant_id,
            company_id=None,
            normalized=dict(second.normalized or {}),
            email=email,
            phone=phone,
            exclude_lead_id=str(second.id),
        )
        assert match.level == "exact"
        assert match.candidate is None
        assert match.prior_lead is not None
        assert str(match.prior_lead.id) == str(first.id)
        assert "lead_email" in match.reasons


@pytest.mark.anyio
async def test_ingest_decision_collapses_onto_prior_open_lead(tenant_id: str) -> None:
    email = f"open-dec-{uuid.uuid4().hex[:10]}@example.com"
    phone = "+48725417332"
    first = _open_lead(tenant_id=tenant_id, email=email, phone=phone, external_id="lg-dec-a")
    second = _open_lead(tenant_id=tenant_id, email=email, phone=phone, external_id="lg-dec-b")
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        session.add_all([first, second])
        await session.commit()

        decision = await evaluate_ingest_decision(
            session,
            DecisionInput.from_normalized(
                tenant_id=tenant_id,
                source="meta",
                normalized=dict(second.normalized or {}),
                current_lead_id=str(second.id),
            ),
            ctx=IngestDecisionContext(effective_processing_mode="assisted"),
            email=email,
            phone=phone,
        )
        assert decision.disposition == IngestDisposition.blocked_duplicate.value
        assert decision.duplicate_match.prior_lead is not None
        assert str(decision.duplicate_match.prior_lead.id) == str(first.id)
        assert "exact_duplicate_lead" in decision.blocking_reasons
