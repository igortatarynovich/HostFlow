"""Recruitment Overview keeps Lead, Candidate, and Application grains apart."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from sqlalchemy import event, text

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.modules.intake_routing.meta_bridge import LEAD_TARGET_CANDIDATE, LEAD_TARGET_CLIENT
from backend.app.services.recruitment_overview_analytics import build_recruitment_overview
from backend.tests.api.test_leads_meta import _ensure_vacancy
from backend.tests.conftest import _set_tenant

OCT_FROM = datetime(2026, 10, 1, tzinfo=timezone.utc)
OCT_TO = datetime(2026, 10, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
NOV_FROM = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _at(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _isolated_day() -> tuple[datetime, datetime, str]:
    """One calendar day outside seeded history, unique per test run."""
    stamp = uuid.uuid4().int
    year = 2400 + (stamp % 400)
    month = (stamp % 12) + 1
    day = (stamp % 27) + 1
    start = datetime(year, month, day, tzinfo=timezone.utc)
    end = datetime(year, month, day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end, f"{year:04d}-{month:02d}-{day:02d}"


@event.listens_for(Candidate, "before_insert")
def _store_candidate_created_at_as_utc_naive(_mapper, _connection, target) -> None:
    created = getattr(target, "created_at", None)
    if created is not None and created.tzinfo is not None:
        target.created_at = created.astimezone(timezone.utc).replace(tzinfo=None)


async def _new_company(db, tenant_id: str) -> str:
    company_id = str(uuid.uuid4())
    await db.execute(
        text(
            """
            INSERT INTO companies (id, tenant_id, name, party_entity_type)
            VALUES (:id, :tenant_id, :name, :party_entity_type)
            """
        ),
        {
            "id": company_id,
            "tenant_id": tenant_id,
            "name": f"Overview {company_id[:8]}",
            "party_entity_type": "company",
        },
    )
    return company_id


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


@pytest.mark.anyio
async def test_two_leads_one_candidate_two_applications(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_a = str(uuid.uuid4())
        lead_b = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="John",
                last_name="Driver",
                email=f"john-ov-{uuid.uuid4().hex[:8]}@example.com",
                stage="contacted",
                status="contacted",
                source="facebook",
                company_id=company_id,
                vacancy_id=vac_a,
                created_at=_at(2026, 10, 1, 9),
            )
        )
        db.add(
            Lead(
                id=lead_a,
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=vac_a,
                source="facebook",
                created_at=_at(2026, 10, 1, 9),
            )
        )
        db.add(
            Lead(
                id=lead_b,
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="duplicated",
                candidate_id=cand_id,
                vacancy_id=vac_b,
                source="website",
                created_at=_at(2026, 10, 15, 9),
            )
        )
        db.add(
            Lead(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                lead_type="client",
                lead_target_type=LEAD_TARGET_CLIENT,
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                source="website",
                created_at=_at(2026, 10, 15, 10),
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=lead_a,
                vacancy_id=vac_a,
                source="facebook",
                applied_at=_at(2026, 10, 1, 9),
                status="applied",
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=lead_b,
                vacancy_id=vac_b,
                source="website",
                applied_at=_at(2026, 10, 15, 9),
                status="applied",
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    acq = body.acquisition
    assert acq.leads_received == 2
    assert acq.unique_candidates_linked == 1
    assert acq.new_candidates == 1
    assert acq.returning_candidates == 1
    assert acq.leads_with_application == 2
    assert acq.leads_duplicated == 1
    sources = {row.source: row for row in acq.by_source}
    assert sources["facebook"].leads == 1
    assert sources["website"].leads == 1
    assert "facebook" in sources and sources["facebook"].leads_with_application == 1
    vacancies = {row.vacancy_id: row for row in acq.by_vacancy}
    assert vacancies[vac_a].leads == 1
    assert vacancies[vac_b].leads == 1
    assert body.people.new_candidates == 1
    assert body.recruitment.applications_started == 2
    null_recruiter = [row for row in body.recruitment.by_recruiter if row.recruiter_id is None]
    assert len(null_recruiter) == 1
    assert null_recruiter[0].applications == 2
    assert body.recruitment.time_basis == "recruitment_application.applied_at"
    assert acq.time_basis == "lead.created_at"
    assert body.people.time_basis == "candidate.created_at"


@pytest.mark.anyio
async def test_october_counts_lead_and_application_not_september_candidate(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Sep",
                last_name="Person",
                email=f"sep-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                created_at=_at(2026, 9, 2),
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="duplicated",
                candidate_id=cand_id,
                vacancy_id=vac_id,
                source="website",
                created_at=_at(2026, 10, 20),
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=lead_id,
                vacancy_id=vac_id,
                source="website",
                applied_at=_at(2026, 10, 20),
                status="applied",
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    assert body.acquisition.leads_received == 1
    assert body.acquisition.returning_candidates == 1
    assert body.acquisition.new_candidates == 0
    assert body.people.new_candidates == 0
    assert body.recruitment.applications_started == 1


@pytest.mark.anyio
async def test_october_candidate_is_not_a_november_application(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Oct",
                last_name="Only",
                email=f"oct-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                created_at=_at(2026, 10, 8),
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=None,
                vacancy_id=vac_id,
                source="portal",
                applied_at=_at(2026, 11, 3),
                status="applied",
            )
        )
        await db.commit()

    october = await _overview(tenant_id, company_id=company_id)
    assert october.people.new_candidates == 1
    assert october.recruitment.applications_started == 0
    november = await _overview(
        tenant_id,
        company_id=company_id,
        period_from="2026-11-01",
        period_to="2026-11-30",
        date_from=NOV_FROM,
        date_to=datetime(2026, 11, 30, 23, 59, 59, 999999, tzinfo=timezone.utc),
    )
    assert november.people.new_candidates == 0
    assert november.recruitment.applications_started == 1


@pytest.mark.anyio
async def test_hired_status_is_current_snapshot_of_started_cohort(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Hired",
                last_name="Later",
                email=f"hired-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                created_at=_at(2026, 1, 1),
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                vacancy_id=vac_id,
                source="meta",
                applied_at=_at(2026, 10, 4),
                status="hired",
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    payload = body.model_dump(by_alias=True)
    assert body.recruitment.applications_started == 1
    hired = [row for row in body.recruitment.by_current_status if row.status == "hired"]
    assert hired and hired[0].count == 1
    assert "hired_in_period" not in payload["recruitment"]
    assert "outcomes_in_period" not in payload["recruitment"]
    assert "application_status_is_current_snapshot_of_started_cohort" in body.limitations


@pytest.mark.anyio
async def test_same_lead_on_two_applications_counts_once_in_acquisition(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Switch",
                last_name="Case",
                email=f"sw-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                created_at=_at(2026, 10, 2),
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=vac_a,
                source="meta",
                created_at=_at(2026, 10, 2),
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=lead_id,
                vacancy_id=vac_a,
                source="meta",
                applied_at=_at(2026, 10, 2),
                status="withdrawn",
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=lead_id,
                vacancy_id=vac_b,
                source="meta",
                applied_at=_at(2026, 10, 9),
                status="applied",
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    assert body.acquisition.leads_received == 1
    assert body.acquisition.leads_with_application == 1
    assert body.recruitment.applications_started == 2


@pytest.mark.anyio
async def test_pool_null_vacancy_is_counted(tenant_id: str) -> None:
    pool_start, pool_end, pool_label = _isolated_day()
    pool_at = pool_start.replace(hour=12)
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Pool",
                last_name="Lead",
                email=f"pool-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=None,
                created_at=pool_at,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={"recruitment_pool_intent_v1": True},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=None,
                source="meta",
                created_at=pool_at,
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=lead_id,
                vacancy_id=None,
                source="meta",
                applied_at=pool_at,
                status="applied",
            )
        )
        await db.commit()

    body = await _overview(
        tenant_id,
        period_from=pool_label,
        period_to=pool_label,
        date_from=pool_start,
        date_to=pool_end,
    )
    assert body.acquisition.leads_received == 1
    assert body.acquisition.leads_with_application == 1
    null_leads = [row for row in body.acquisition.by_vacancy if row.vacancy_id is None]
    assert len(null_leads) == 1
    assert null_leads[0].leads == 1
    assert null_leads[0].vacancy_name is None
    assert body.recruitment.applications_started == 1
    null_apps = [row for row in body.recruitment.by_vacancy if row.vacancy_id is None]
    assert len(null_apps) == 1
    assert null_apps[0].applications == 1


@pytest.mark.anyio
async def test_other_tenant_does_not_affect_any_section(tenant_id: str) -> None:
    other = str(uuid.uuid4())
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        db.add(
            Tenant(
                id=other,
                name=f"ov-{other[:8]}",
                slug=f"ov-{other[:8]}",
                api_key=f"ov-{other[:8]}",
                is_active=True,
                type=TenantType.agency,
                status=TenantStatus.active,
            )
        )
        await db.flush()
        await _set_tenant(db, other)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=other,
                first_name="Other",
                last_name="Tenant",
                email=f"other-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                created_at=_at(2090, 7, 6),
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=other,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                source="facebook",
                created_at=_at(2090, 7, 6),
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=other,
                candidate_id=cand_id,
                lead_id=lead_id,
                vacancy_id=None,
                source="facebook",
                applied_at=_at(2090, 7, 6),
                status="applied",
            )
        )
        await db.commit()

    body = await _overview(
        tenant_id,
        period_from="2090-07-01",
        period_to="2090-07-31",
        date_from=_at(2090, 7, 1, 0),
        date_to=datetime(2090, 7, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
    )
    assert body.acquisition.leads_received == 0
    assert body.acquisition.unique_candidates_linked == 0
    assert body.people.new_candidates == 0
    assert body.recruitment.applications_started == 0
    assert body.historical_gap.linked_recruitment_leads_without_application == 0


@pytest.mark.anyio
async def test_company_filter_excludes_pool_application_without_vacancy(tenant_id: str) -> None:
    day_start, day_end, day_label = _isolated_day()
    day_at = day_start.replace(hour=12)
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Co",
                last_name="Filter",
                email=f"co-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                created_at=day_at,
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                vacancy_id=vac_id,
                source="meta",
                applied_at=day_at,
                status="applied",
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                vacancy_id=None,
                source="meta",
                applied_at=day_at.replace(hour=13),
                status="applied",
            )
        )
        await db.commit()

    period = dict(
        period_from=day_label,
        period_to=day_label,
        date_from=day_start,
        date_to=day_end,
    )
    unfiltered = await _overview(tenant_id, **period)
    filtered = await _overview(tenant_id, company_id=company_id, **period)
    assert unfiltered.recruitment.applications_started == 2
    assert filtered.recruitment.applications_started == 1
    assert filtered.recruitment.by_vacancy[0].vacancy_id == vac_id


@pytest.mark.anyio
async def test_vacancy_filter_people_ignores_current_candidate_vacancy(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Proj",
                last_name="Vac",
                email=f"proj-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=vac_b,
                created_at=_at(2026, 10, 11),
            )
        )
        db.add(
            Lead(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=vac_a,
                source="meta",
                created_at=_at(2026, 10, 11),
            )
        )
        await db.commit()

    on_inbound = await _overview(tenant_id, company_id=company_id, vacancy_id=vac_a)
    on_projection = await _overview(tenant_id, company_id=company_id, vacancy_id=vac_b)
    assert on_inbound.people.new_candidates == 1
    assert on_inbound.acquisition.leads_received == 1
    assert on_projection.people.new_candidates == 0
    assert on_projection.acquisition.leads_received == 0


@pytest.mark.anyio
async def test_linked_lead_without_application_is_gap_not_started_count(tenant_id: str) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        cand_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Gap",
                last_name="Only",
                email=f"gap-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                created_at=_at(2026, 10, 12),
            )
        )
        db.add(
            Lead(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="duplicated",
                candidate_id=cand_id,
                vacancy_id=None,
                source="website",
                created_at=_at(2026, 10, 12),
            )
        )
        db.add(
            Lead(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="duplicate_review",
                candidate_id=cand_id,
                source="website",
                created_at=_at(2026, 10, 12, 15),
            )
        )
        await db.commit()

    body = await _overview(tenant_id, company_id=company_id)
    assert body.acquisition.leads_received == 2
    assert body.acquisition.leads_duplicated == 1
    assert body.acquisition.leads_in_duplicate_review == 1
    assert body.acquisition.leads_with_application == 0
    assert body.recruitment.applications_started == 0
    assert body.historical_gap.linked_recruitment_leads_without_application == 1


@pytest.mark.anyio
async def test_recruitment_overview_http_returns_separate_sections(
    client, manager_headers, tenant_id: str
) -> None:
    async with async_session_maker() as db:
        await _set_tenant(db, tenant_id)
        company_id = await _new_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Http",
                last_name="John",
                email=f"http-{uuid.uuid4().hex[:8]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                created_at=_at(2026, 10, 1),
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                lead_target_type=LEAD_TARGET_CANDIDATE,
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=vac_id,
                source="facebook",
                created_at=_at(2026, 10, 1),
            )
        )
        db.add(
            RecruitmentApplication(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                candidate_id=cand_id,
                lead_id=lead_id,
                vacancy_id=vac_id,
                source="facebook",
                applied_at=_at(2026, 10, 1),
                status="applied",
            )
        )
        await db.commit()

    response = await client.get(
        "/api/v1/analytics/recruitment-overview",
        headers=manager_headers,
        params={"from": "2026-10-01", "to": "2026-10-31", "company_id": company_id},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["period"]["from"] == "2026-10-01"
    assert payload["period"]["to"] == "2026-10-31"
    assert payload["acquisition"]["time_basis"] == "lead.created_at"
    assert payload["acquisition"]["leads_received"] == 1
    assert payload["people"]["new_candidates"] == 1
    assert payload["recruitment"]["applications_started"] == 1
    assert payload["people"]["time_basis"] == "candidate.created_at"
    assert payload["recruitment"]["time_basis"] == "recruitment_application.applied_at"
    assert "by_current_status" in payload["recruitment"]
    assert "hired_in_period" not in payload["recruitment"]
