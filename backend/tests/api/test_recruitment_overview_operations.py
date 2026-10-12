"""Operational recruitment analytics: stages, contacts, and reasons.

Each metric uses its own timestamp. Current stage and current reasons ignore
the selected date range. Company and vacancy filters on stage history and
contact attempts use the candidate's current assignment.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.models.contact_attempt import ContactAttempt
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.modules.intake_routing.meta_bridge import LEAD_TARGET_CANDIDATE
from backend.app.services.recruitment_overview_analytics import (
    CURRENT_CANDIDATE_PROJECTION,
    FILTER_NOT_REQUESTED,
    LIMITATION_CODES,
    build_recruitment_overview,
)
from backend.tests.api.test_leads_meta import _ensure_vacancy
from backend.tests.api.test_recruitment_overview_analytics import (
    _at,
    _isolated_day,
    _new_company,
)
from backend.tests.conftest import _set_tenant

OCT_FROM = datetime(2026, 10, 1, tzinfo=timezone.utc)
OCT_TO = datetime(2026, 10, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)


async def _overview(tenant_id: str, **kwargs):
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        return await build_recruitment_overview(
            db,
            tenant_id=tenant_id,
            period_from=kwargs.pop("period_from", "2026-10-01"),
            period_to=kwargs.pop("period_to", "2026-10-31"),
            date_from=kwargs.pop("date_from", OCT_FROM),
            date_to=kwargs.pop("date_to", OCT_TO),
            **kwargs,
        )


def _candidate(
    *,
    tenant_id: str,
    company_id: str,
    vacancy_id: str | None,
    created_at: datetime,
    stage: str,
    reasons: list[str] | None = None,
) -> Candidate:
    return Candidate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name="Ops",
        last_name=uuid.uuid4().hex[:6],
        email=f"ops-{uuid.uuid4().hex[:8]}@example.com",
        stage=stage,
        status=stage,
        source="website",
        company_id=company_id,
        vacancy_id=vacancy_id,
        status_reason=reasons,
        created_at=created_at,
    )


def _history(
    *,
    tenant_id: str,
    candidate_id: str,
    at: datetime,
    to_code: str,
    from_code: str | None = None,
) -> CandidateStageHistory:
    return CandidateStageHistory(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        from_code=from_code,
        to_code=to_code,
        at=at,
    )


def _attempt(
    *,
    candidate_id: str,
    at: datetime,
    result: str,
    channel: str = "call",
    number: int = 1,
) -> ContactAttempt:
    return ContactAttempt(
        id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        attempt_number=number,
        attempted_at=at,
        channel=channel,
        result=result,
    )


@pytest.mark.anyio
async def test_contact_attempts_count_attempted_at_not_candidate_created_at(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        candidate = _candidate(
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=None,
            created_at=_at(2026, 9, 1),
            stage="contacted",
        )
        db.add(candidate)
        db.add(_attempt(candidate_id=candidate.id, at=_at(2026, 10, 5), result="answered", number=1))
        db.add(
            _attempt(
                candidate_id=candidate.id,
                at=_at(2026, 10, 10),
                result="no_answer",
                channel="whatsapp",
                number=2,
            )
        )
        db.add(_attempt(candidate_id=candidate.id, at=_at(2026, 11, 2), result="answered", number=3))
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    assert body.contacts.time_basis == "contact_attempt.attempted_at"
    assert body.contacts.attempts_total == 2
    assert body.contacts.candidates_contacted == 1
    assert body.contacts.successful_attempts == 1
    assert body.contacts.successful_contact_rule == "result_equals_answered"
    assert {row.result: row.attempts for row in body.contacts.by_result} == {
        "answered": 1,
        "no_answer": 1,
    }
    assert {row.channel: row.attempts for row in body.contacts.by_channel} == {
        "call": 1,
        "whatsapp": 1,
    }
    assert body.contacts.vacancy_attribution == CURRENT_CANDIDATE_PROJECTION
    assert body.people.new_candidates == 0


@pytest.mark.anyio
async def test_stage_transitions_count_history_at_not_creation_cohort(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        candidate = _candidate(
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=None,
            created_at=_at(2026, 8, 1),
            stage="hired",
        )
        db.add(candidate)
        db.add(_history(tenant_id=tenant_id, candidate_id=candidate.id, at=_at(2026, 9, 2), to_code="contacted"))
        db.add(
            _history(
                tenant_id=tenant_id,
                candidate_id=candidate.id,
                at=_at(2026, 10, 8),
                from_code="contacted",
                to_code="docs_wait",
            )
        )
        db.add(
            _history(
                tenant_id=tenant_id,
                candidate_id=candidate.id,
                at=_at(2026, 11, 3),
                from_code="docs_wait",
                to_code="hired",
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    assert body.stages.transitions.time_basis == "candidate_stage_history.at"
    assert body.stages.transitions.total == 1
    entered = {row.stage: row.count for row in body.stages.transitions.entered_by_stage}
    assert entered == {"docs_wait": 1}
    assert body.stages.transitions.by_transition[0].from_stage == "contacted"
    assert body.stages.transitions.by_transition[0].to_stage == "docs_wait"
    assert body.stages.current.date_range_applied is False
    current = {row.stage: row.candidates for row in body.stages.current.by_stage}
    assert current.get("hired") == 1
    assert "docs_wait" not in current


@pytest.mark.anyio
async def test_current_stage_snapshot_does_not_mean_entered_in_period(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        db.add(
            _candidate(
                tenant_id=tenant_id,
                company_id=company_id,
                vacancy_id=None,
                created_at=_at(2026, 8, 4),
                stage="docs_wait",
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    assert body.stages.current.semantics == "current_candidate_stage_snapshot"
    assert body.stages.current.date_range_applied is False
    assert body.stages.current.total_candidates == 1
    assert body.stages.current.by_stage[0].stage == "docs_wait"
    assert body.stages.transitions.total == 0
    assert body.people.new_candidates == 0


@pytest.mark.anyio
async def test_reason_snapshot_is_not_a_period_rejection(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        db.add(
            _candidate(
                tenant_id=tenant_id,
                company_id=company_id,
                vacancy_id=None,
                created_at=_at(2026, 8, 4),
                stage="rejected",
                reasons=["salary", "location"],
            )
        )
        db.add(
            _candidate(
                tenant_id=tenant_id,
                company_id=company_id,
                vacancy_id=None,
                created_at=_at(2026, 8, 5),
                stage="declined",
                reasons=["schedule"],
            )
        )
        db.add(
            _candidate(
                tenant_id=tenant_id,
                company_id=company_id,
                vacancy_id=None,
                created_at=_at(2026, 8, 6),
                stage="rejected",
                reasons=["salary"],
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    assert body.reasons.semantics == "current_candidate_status_reason_snapshot"
    assert body.reasons.date_range_applied is False
    assert body.reasons.rejected.candidates == 2
    rejected = {row.reason: (row.candidates, row.occurrences) for row in body.reasons.rejected.by_reason}
    assert rejected["salary"] == (2, 2)
    assert rejected["location"] == (1, 1)
    assert body.reasons.declined.candidates == 1
    assert body.reasons.declined.by_reason[0].reason == "schedule"
    assert body.reasons.declined.by_reason[0].candidates == 1
    assert body.stages.transitions.total == 0


@pytest.mark.anyio
async def test_client_and_vacancy_slices_follow_documented_attribution(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_a = await _new_company(db, tenant_id)
        company_b = await _new_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_a)
        vac_b = await _ensure_vacancy(db, tenant_id, company_a)
        vac_c = await _ensure_vacancy(db, tenant_id, company_b)

        cand_a = _candidate(
            tenant_id=tenant_id,
            company_id=company_a,
            vacancy_id=vac_a,
            created_at=_at(2026, 8, 1),
            stage="docs_wait",
        )
        cand_b = _candidate(
            tenant_id=tenant_id,
            company_id=company_a,
            vacancy_id=vac_b,
            created_at=_at(2026, 9, 1),
            stage="rejected",
            reasons=["salary"],
        )
        cand_c = _candidate(
            tenant_id=tenant_id,
            company_id=company_b,
            vacancy_id=vac_c,
            created_at=_at(2026, 10, 3),
            stage="declined",
            reasons=["schedule"],
        )
        db.add_all([cand_a, cand_b, cand_c])
        db.add(
            _history(
                tenant_id=tenant_id,
                candidate_id=cand_a.id,
                at=_at(2026, 10, 6),
                from_code="contacted",
                to_code="docs_wait",
            )
        )
        db.add(
            _history(
                tenant_id=tenant_id,
                candidate_id=cand_c.id,
                at=_at(2026, 10, 7),
                to_code="declined",
            )
        )
        db.add(_attempt(candidate_id=cand_a.id, at=_at(2026, 10, 5), result="answered"))
        db.add(
            _attempt(
                candidate_id=cand_b.id,
                at=_at(2026, 10, 10),
                result="no_answer",
                channel="email",
            )
        )
        db.add(_attempt(candidate_id=cand_c.id, at=_at(2026, 10, 11), result="unavailable"))
        for cand, vacancy, company in (
            (cand_a, vac_a, company_a),
            (cand_b, vac_b, company_a),
            (cand_c, vac_c, company_b),
        ):
            lead_id = str(uuid.uuid4())
            db.add(
                Lead(
                    id=lead_id,
                    tenant_id=tenant_id,
                    lead_type="candidate",
                    lead_target_type=LEAD_TARGET_CANDIDATE,
                    company_id=company,
                    payload={},
                    normalized={},
                    status="processed",
                    candidate_id=cand.id,
                    vacancy_id=vacancy,
                    source="website",
                    created_at=_at(2026, 10, 4),
                )
            )
            db.add(
                RecruitmentApplication(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    candidate_id=cand.id,
                    lead_id=lead_id,
                    vacancy_id=vacancy,
                    source="website",
                    applied_at=_at(2026, 10, 4),
                    status="applied",
                )
            )
        await db.commit()

    company_a_body = await _overview(tenant_id, company_id=company_a)
    assert company_a_body.acquisition.leads_received == 2
    assert company_a_body.recruitment.applications_started == 2
    assert company_a_body.stages.current.total_candidates == 2
    assert {row.stage for row in company_a_body.stages.current.by_stage} == {"docs_wait", "rejected"}
    assert company_a_body.stages.transitions.total == 1
    assert company_a_body.stages.transitions.vacancy_attribution == CURRENT_CANDIDATE_PROJECTION
    assert company_a_body.contacts.attempts_total == 2
    assert company_a_body.contacts.vacancy_attribution == CURRENT_CANDIDATE_PROJECTION
    assert company_a_body.reasons.rejected.candidates == 1
    assert company_a_body.reasons.declined.candidates == 0

    vacancy_b = await _overview(tenant_id, company_id=company_a, vacancy_id=vac_b)
    assert vacancy_b.acquisition.leads_received == 1
    assert vacancy_b.recruitment.applications_started == 1
    assert vacancy_b.stages.current.total_candidates == 1
    assert vacancy_b.stages.current.by_stage[0].stage == "rejected"
    assert vacancy_b.stages.transitions.total == 0
    assert vacancy_b.contacts.attempts_total == 1
    assert vacancy_b.contacts.by_result[0].result == "no_answer"
    assert vacancy_b.reasons.rejected.by_reason[0].reason == "salary"

    vacancy_a = await _overview(tenant_id, vacancy_id=vac_a)
    assert vacancy_a.stages.transitions.total == 1
    assert vacancy_a.stages.transitions.entered_by_stage[0].stage == "docs_wait"
    assert vacancy_a.contacts.attempts_total == 1
    assert vacancy_a.reasons.rejected.candidates == 0

    company_b_body = await _overview(tenant_id, company_id=company_b)
    assert company_b_body.acquisition.leads_received == 1
    assert company_b_body.recruitment.applications_started == 1
    assert company_b_body.stages.current.by_stage[0].stage == "declined"
    assert company_b_body.contacts.attempts_total == 1
    assert company_b_body.reasons.declined.by_reason[0].reason == "schedule"
    assert company_b_body.people.new_candidates == 1


@pytest.mark.anyio
async def test_unfiltered_transitions_are_exact_and_other_tenant_is_excluded(tenant_id: str) -> None:
    start, end, label = _isolated_day()
    other = str(uuid.uuid4())
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        candidate = _candidate(
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=None,
            created_at=start,
            stage="contacted",
        )
        db.add(candidate)
        db.add(_history(tenant_id=tenant_id, candidate_id=candidate.id, at=start, to_code="contacted"))
        db.add(_attempt(candidate_id=candidate.id, at=start, result="answered"))
        db.add(
            Tenant(
                id=other,
                name=f"ops-{other[:8]}",
                slug=f"ops-{other[:8]}",
                api_key=f"ops-{other[:8]}",
                is_active=True,
                type=TenantType.agency,
                status=TenantStatus.active,
            )
        )
        await db.flush()
        await _set_tenant(db, other)
        other_company = await _new_company(db, other)
        other_candidate = _candidate(
            tenant_id=other,
            company_id=other_company,
            vacancy_id=None,
            created_at=start,
            stage="rejected",
            reasons=["salary"],
        )
        db.add(other_candidate)
        db.add(_history(tenant_id=other, candidate_id=other_candidate.id, at=start, to_code="rejected"))
        db.add(_attempt(candidate_id=other_candidate.id, at=start, result="no_answer"))
        await db.commit()

    body = await _overview(
        tenant_id,
        period_from=label,
        period_to=label,
        date_from=start,
        date_to=end,
    )
    assert body.stages.transitions.total == 1
    assert body.stages.transitions.vacancy_attribution == FILTER_NOT_REQUESTED
    assert body.contacts.attempts_total == 1
    assert body.contacts.company_attribution == FILTER_NOT_REQUESTED
    assert "stage_history_has_no_event_time_vacancy" in body.limitations
    assert "contact_attempt_has_no_event_time_vacancy" in body.limitations
    assert "current_stage_snapshot_ignores_selected_date_range" in LIMITATION_CODES
    assert "stage_history_omits_some_stage_writes" not in body.limitations
