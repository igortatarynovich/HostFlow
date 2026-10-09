"""Exact-duplicate Lead → existing Candidate → RecruitmentApplication continuity.

Auto path must reuse lead-intent ensure without projecting Candidate.vacancy_id
or Candidate.stage. C2a (distinct lead_id → distinct application) stays as-is.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.decision_layer import (
    DecisionInput,
    DecisionResult,
    IngestDecisionContext,
    IngestDisposition,
    evaluate_ingest_decision,
)
from backend.app.entity_profile.outcome_executor import apply_blocked_duplicate_outcome
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.modules.leads.duplicate_resolution import LeadDuplicateMatch
from backend.app.services.outcome_resolver import OutcomeResolution
from backend.app.services.recruitment_application_lifecycle import (
    set_recruitment_application_status,
)
from backend.app.services.recruitment_application_service import (
    ensure_recruitment_application_for_lead_intent,
    switch_recruitment_application_vacancy,
)
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


def _blocked_decision(candidate: Candidate) -> DecisionResult:
    return DecisionResult(
        disposition=IngestDisposition.blocked_duplicate.value,
        outcome_resolution=OutcomeResolution(),
        duplicate_match=LeadDuplicateMatch(
            level="exact",
            candidate=candidate,
            reasons=["email"],
            hr_blockers=[],
        ),
        may_create_candidate=False,
        attach_candidate_id=str(candidate.id),
    )


async def _app_count(db, *, tenant_id: str, candidate_id: str) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(RecruitmentApplication)
        .where(
            RecruitmentApplication.tenant_id == tenant_id,
            RecruitmentApplication.candidate_id == candidate_id,
        )
    )
    return int(res.scalar_one() or 0)


async def _seed_candidate(
    db,
    *,
    tenant_id: str,
    company_id: str,
    vacancy_id: str | None,
    stage: str = "contacted",
    source: str = "facebook",
) -> Candidate:
    cand = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name="John",
        last_name="Driver",
        email=f"john-{uuid.uuid4().hex[:10]}@example.com",
        stage=stage,
        status=stage,
        source=source,
        company_id=company_id,
        vacancy_id=vacancy_id,
    )
    db.add(cand)
    await db.flush()
    return cand


def _lead(
    *,
    tenant_id: str,
    company_id: str,
    vacancy_id: str | None,
    source: str = "website",
    normalized: dict | None = None,
    status: str = "new",
) -> Lead:
    return Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        lead_type="candidate",
        company_id=company_id,
        payload={},
        normalized=dict(normalized or {}),
        status=status,
        vacancy_id=vacancy_id,
        source=source,
    )


@pytest.mark.anyio
async def test_exact_duplicate_new_vacancy_creates_application_without_projection(
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_b, source="website")
        db.add(lead)
        await db.commit()
        cand_id, lead_id = str(cand.id), str(lead.id)

    async with async_session_maker() as db:
        cand = await db.get(Candidate, cand_id)
        lead = await db.get(Lead, lead_id)
        assert cand is not None and lead is not None
        await apply_blocked_duplicate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized={},
            decision=_blocked_decision(cand),
            resolved_company_id=company_id,
        )

    async with async_session_maker() as db:
        cand = await db.get(Candidate, cand_id)
        lead = await db.get(Lead, lead_id)
        assert cand is not None and lead is not None
        assert str(lead.candidate_id) == cand_id
        assert lead.status == "duplicated"
        assert str(cand.vacancy_id) == vac_a
        assert str(cand.stage) == "contacted"
        assert str(cand.source) == "facebook"
        apps = (
            await db.execute(
                select(RecruitmentApplication).where(
                    RecruitmentApplication.tenant_id == tenant_id,
                    RecruitmentApplication.lead_id == lead_id,
                )
            )
        ).scalars().all()
        assert len(apps) == 1
        assert apps[0].vacancy_id == vac_b
        assert apps[0].source == "website"
        assert apps[0].candidate_id == cand_id
        assert apps[0].application_cycle is None


@pytest.mark.anyio
async def test_exact_duplicate_same_vacancy_new_lead_second_application(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead_a = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a, source="facebook")
        lead_a.status = "processed"
        lead_a.candidate_id = str(cand.id)
        lead_b = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a, source="website")
        db.add(lead_a)
        db.add(lead_b)
        await db.commit()
        cand_id, lead_a_id, lead_b_id = str(cand.id), str(lead_a.id), str(lead_b.id)

    async with async_session_maker() as db:
        first = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_a_id,
            vacancy_id=vac_a,
            source="facebook",
        )
        assert first is not None
        await db.commit()

    async with async_session_maker() as db:
        cand = await db.get(Candidate, cand_id)
        lead_b = await db.get(Lead, lead_b_id)
        assert cand is not None and lead_b is not None
        await apply_blocked_duplicate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead_b,
            normalized={},
            decision=_blocked_decision(cand),
            resolved_company_id=company_id,
        )

    async with async_session_maker() as db:
        rows = (
            await db.execute(
                select(RecruitmentApplication).where(
                    RecruitmentApplication.tenant_id == tenant_id,
                    RecruitmentApplication.candidate_id == cand_id,
                )
            )
        ).scalars().all()
        assert len(rows) == 2
        by_lead = {str(row.lead_id): row for row in rows}
        assert set(by_lead) == {lead_a_id, lead_b_id}
        assert by_lead[lead_a_id].vacancy_id == vac_a
        assert by_lead[lead_b_id].vacancy_id == vac_a
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        assert str(cand.vacancy_id) == vac_a
        assert str(cand.stage) == "contacted"


@pytest.mark.anyio
async def test_exact_duplicate_without_vacancy_or_pool_creates_no_application(
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=None)
        db.add(lead)
        await db.commit()
        cand_id, lead_id = str(cand.id), str(lead.id)

    async with async_session_maker() as db:
        cand = await db.get(Candidate, cand_id)
        lead = await db.get(Lead, lead_id)
        assert cand is not None and lead is not None
        await apply_blocked_duplicate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized={},
            decision=_blocked_decision(cand),
            resolved_company_id=company_id,
        )

    async with async_session_maker() as db:
        assert await _app_count(db, tenant_id=tenant_id, candidate_id=cand_id) == 0
        cand = await db.get(Candidate, cand_id)
        lead = await db.get(Lead, lead_id)
        assert cand is not None and lead is not None
        assert str(cand.vacancy_id) == vac_a
        assert lead.vacancy_id is None
        assert str(cand.stage) == "contacted"
        assert str(cand.source) == "facebook"


@pytest.mark.anyio
async def test_exact_duplicate_pool_intent_creates_null_vacancy_application(
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead = _lead(
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=None,
            normalized={"recruitment_pool_intent_v1": True},
        )
        db.add(lead)
        await db.commit()
        cand_id, lead_id = str(cand.id), str(lead.id)

    async with async_session_maker() as db:
        cand = await db.get(Candidate, cand_id)
        lead = await db.get(Lead, lead_id)
        assert cand is not None and lead is not None
        await apply_blocked_duplicate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized={"recruitment_pool_intent_v1": True},
            decision=_blocked_decision(cand),
            resolved_company_id=company_id,
        )

    async with async_session_maker() as db:
        apps = (
            await db.execute(
                select(RecruitmentApplication).where(
                    RecruitmentApplication.tenant_id == tenant_id,
                    RecruitmentApplication.lead_id == lead_id,
                )
            )
        ).scalars().all()
        assert len(apps) == 1
        assert apps[0].vacancy_id is None
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        assert str(cand.vacancy_id) == vac_a
        assert str(cand.stage) == "contacted"


@pytest.mark.anyio
async def test_exact_duplicate_replay_does_not_create_another_application(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_b)
        db.add(lead)
        await db.commit()
        cand_id, lead_id = str(cand.id), str(lead.id)

    for _ in range(2):
        async with async_session_maker() as db:
            cand = await db.get(Candidate, cand_id)
            lead = await db.get(Lead, lead_id)
            assert cand is not None and lead is not None
            await apply_blocked_duplicate_outcome(
                db,
                tenant_id=tenant_id,
                lead=lead,
                normalized={},
                decision=_blocked_decision(cand),
                resolved_company_id=company_id,
            )

    async with async_session_maker() as db:
        assert await _app_count(db, tenant_id=tenant_id, candidate_id=cand_id) == 1
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        assert str(cand.vacancy_id) == vac_a
        assert str(cand.stage) == "contacted"


@pytest.mark.anyio
async def test_null_vacancy_replay_still_creates_no_application(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=None)
        db.add(lead)
        await db.commit()
        cand_id, lead_id = str(cand.id), str(lead.id)

    for _ in range(2):
        async with async_session_maker() as db:
            cand = await db.get(Candidate, cand_id)
            lead = await db.get(Lead, lead_id)
            assert cand is not None and lead is not None
            await apply_blocked_duplicate_outcome(
                db,
                tenant_id=tenant_id,
                lead=lead,
                normalized={},
                decision=_blocked_decision(cand),
                resolved_company_id=company_id,
            )

    async with async_session_maker() as db:
        assert await _app_count(db, tenant_id=tenant_id, candidate_id=cand_id) == 0
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        assert str(cand.vacancy_id) == vac_a


@pytest.mark.anyio
async def test_workforce_blocker_stays_duplicate_review_without_application(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(
            db, tenant_id=tenant_id, company_id=company_id, vacancy_id=None, stage="ready_for_hr"
        )
        cand.email = f"locked-{uuid.uuid4().hex[:8]}@example.com"
        db.add(
            WorkforceEmployee(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=str(cand.id),
                display_name="Locked John",
                status="onboarding",
            )
        )
        lead = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_b)
        lead.status = "duplicate_review"
        db.add(lead)
        await db.commit()
        cand_id, lead_id, email = str(cand.id), str(lead.id), str(cand.email)

    async with async_session_maker() as db:
        decision = await evaluate_ingest_decision(
            db,
            DecisionInput.from_normalized(
                tenant_id=tenant_id,
                source="meta",
                normalized={
                    "ingest_envelope_v1": {
                        "route_intent": RouteIntent.candidate_application.value,
                    }
                },
                company_id=company_id,
            ),
            ctx=IngestDecisionContext(
                may_auto_convert=True,
                triage_gate_bypass=True,
                vacancy_resolved=True,
            ),
            email=email,
            phone=None,
        )
        assert decision.disposition == IngestDisposition.review_queue.value
        assert decision.duplicate_match.needs_duplicate_review is True
        assert "workforce" in decision.duplicate_match.hr_blockers
        refused = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_b,
            source="website",
            sync_candidate_vacancy=False,
        )
        assert refused is None
        assert await _app_count(db, tenant_id=tenant_id, candidate_id=cand_id) == 0
        lead = await db.get(Lead, lead_id)
        assert lead is not None
        assert lead.status == "duplicate_review"


@pytest.mark.anyio
async def test_returned_to_recruitment_creates_application_without_projection(
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        cand.email = f"returned-{uuid.uuid4().hex[:8]}@example.com"
        db.add(
            WorkforceEmployee(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=str(cand.id),
                display_name="Returned John",
                status="returned_to_recruitment",
            )
        )
        lead = _lead(tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_b)
        db.add(lead)
        await db.commit()
        cand_id, lead_id, email = str(cand.id), str(lead.id), str(cand.email)

    async with async_session_maker() as db:
        decision = await evaluate_ingest_decision(
            db,
            DecisionInput.from_normalized(
                tenant_id=tenant_id,
                source="meta",
                normalized={
                    "ingest_envelope_v1": {
                        "route_intent": RouteIntent.candidate_application.value,
                    }
                },
                company_id=company_id,
            ),
            ctx=IngestDecisionContext(
                may_auto_convert=True,
                triage_gate_bypass=True,
                vacancy_resolved=True,
            ),
            email=email,
            phone=None,
        )
        assert decision.disposition == IngestDisposition.blocked_duplicate.value
        assert decision.duplicate_match.hr_blockers == []
        lead = await db.get(Lead, lead_id)
        cand = await db.get(Candidate, cand_id)
        assert lead is not None and cand is not None
        await apply_blocked_duplicate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized={},
            decision=decision,
            resolved_company_id=company_id,
        )

    async with async_session_maker() as db:
        apps = (
            await db.execute(
                select(RecruitmentApplication).where(
                    RecruitmentApplication.tenant_id == tenant_id,
                    RecruitmentApplication.lead_id == lead_id,
                )
            )
        ).scalars().all()
        assert len(apps) == 1
        assert apps[0].vacancy_id == vac_b
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        assert str(cand.vacancy_id) == vac_a
        assert str(cand.stage) == "contacted"
        assert str(cand.source) == "facebook"


@pytest.mark.anyio
async def test_ensure_replay_after_vacancy_switch_does_not_insert_third_row(
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead = _lead(
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=vac_a,
            source="meta",
            status="processed",
        )
        lead.candidate_id = str(cand.id)
        db.add(lead)
        await db.commit()
        cand_id, lead_id = str(cand.id), str(lead.id)

    async with async_session_maker() as db:
        app = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_a,
            source="meta",
        )
        assert app is not None
        set_recruitment_application_status(app, "in_review")
        await db.commit()
        app_id = str(app.id)

    async with async_session_maker() as db:
        prev, switched = await switch_recruitment_application_vacancy(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            application_id=app_id,
            to_vacancy_id=vac_b,
        )
        assert switched.id != prev.id
        assert str(switched.lead_id) == lead_id
        assert str(prev.lead_id) == lead_id
        await db.commit()

    async with async_session_maker() as db:
        again = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_b,
            source="meta",
        )
        assert again is not None
        await db.commit()

    async with async_session_maker() as db:
        rows = (
            await db.execute(
                select(RecruitmentApplication)
                .where(
                    RecruitmentApplication.tenant_id == tenant_id,
                    RecruitmentApplication.lead_id == lead_id,
                )
                .order_by(RecruitmentApplication.created_at.asc())
            )
        ).scalars().all()
        assert len(rows) == 2
        assert {row.vacancy_id for row in rows} == {vac_a, vac_b}


@pytest.mark.anyio
async def test_default_ensure_still_syncs_candidate_vacancy(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand = await _seed_candidate(db, tenant_id=tenant_id, company_id=company_id, vacancy_id=vac_a)
        lead = _lead(
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=vac_b,
            source="meta",
            status="processed",
        )
        lead.candidate_id = str(cand.id)
        db.add(lead)
        await db.commit()
        cand_id, lead_id = str(cand.id), str(lead.id)

    async with async_session_maker() as db:
        app = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_b,
            source="meta",
        )
        assert app is not None
        assert app.vacancy_id == vac_b
        cand = await db.get(Candidate, cand_id)
        assert cand is not None
        assert str(cand.vacancy_id) == vac_b
        assert str(cand.stage) == "contacted"
        await db.commit()
