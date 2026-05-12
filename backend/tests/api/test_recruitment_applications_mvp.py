"""Recruitment application MVP — service + pool semantics (see application-creation-mvp.md).

Regression targets (manual / prod smoke can mirror these):

- Meta lead → process → Candidate → one Application per lead_id (when vacancy or explicit pool intent)
- duplicate attach_existing / exact duplicate → Application when vacancy or explicit intent
- repeat process / webhook redelivery → still one Application per (candidate_id, lead_id)
- pool (no vacancy) → Application only with ``recruitment_pool_intent_v1`` or ``funnel_id``
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.services.recruitment_application_service import (
    ensure_recruitment_application_for_lead_intent,
)
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


@pytest.mark.anyio
async def test_ensure_recruitment_application_pool_explicit_intent_vacancy_null(
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Pool",
                last_name="Applicant",
                email=f"pool-app-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=None,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={"recruitment_pool_intent_v1": True},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=None,
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        app = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=None,
            source="meta",
        )
        assert app is not None
        assert app.vacancy_id is None
        assert app.status == "applied"
        await db.commit()

    async with async_session_maker() as db:
        cnt = await db.execute(
            select(func.count())
            .select_from(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.lead_id == lead_id,
            )
        )
        assert int(cnt.scalar_one() or 0) == 1


@pytest.mark.anyio
async def test_ensure_skips_pool_without_explicit_intent(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Bare",
                last_name="Pool",
                email=f"bare-pool-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=None,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=None,
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        out = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=None,
            source="meta",
        )
        assert out is None
        await db.rollback()


@pytest.mark.anyio
async def test_ensure_skips_lead_in_duplicate_review(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Dup",
                last_name="Review",
                email=f"duprev-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=vac_id,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={},
                status="duplicate_review",
                candidate_id=None,
                vacancy_id=vac_id,
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        out = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        assert out is None


@pytest.mark.anyio
async def test_ensure_idempotent_by_candidate_and_lead(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Idemp",
                last_name="App",
                email=f"idemp-app-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=vac_id,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=vac_id,
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        a1 = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        assert a1 is not None
        a2 = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        assert a2 is not None
        assert a1.id == a2.id
        await db.commit()

    async with async_session_maker() as db:
        cnt = await db.execute(
            select(func.count())
            .select_from(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.candidate_id == cand_id,
                RecruitmentApplication.lead_id == lead_id,
            )
        )
        assert int(cnt.scalar_one() or 0) == 1


@pytest.mark.anyio
async def test_get_candidate_applications_legacy_candidate_empty_list(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    """Candidate row without any Application → GET returns 200 and []."""
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        cid = str(uuid.uuid4())
        session.add(
            Candidate(
                id=cid,
                tenant_id=tenant_id,
                first_name="Legacy",
                last_name="NoApp",
                email=f"leg-no-app-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
            )
        )
        await session.commit()

    r = await client.get(
        f"/api/v1/candidates/{cid}/applications",
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.anyio
async def test_get_candidate_applications_pool_vacancy_null_in_json(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    """GET serializes vacancy_id null for pool-style applications (explicit intent)."""
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Pool",
                last_name="Api",
                email=f"pool-api-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=None,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={"recruitment_pool_intent_v1": True},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=None,
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=None,
            source="meta",
        )
        await db.commit()

    r = await client.get(
        f"/api/v1/candidates/{cand_id}/applications",
        headers=manager_headers,
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["vacancy_id"] is None
    assert items[0]["lead_id"] == lead_id
    assert items[0]["status"] == "applied"


@pytest.mark.anyio
async def test_ensure_does_not_change_candidate_stage(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Stage",
                last_name="Stable",
                email=f"stage-stable-{uuid.uuid4().hex[:10]}@example.com",
                stage="contacted",
                status="new",
                company_id=company_id,
                vacancy_id=vac_id,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=vac_id,
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        cand_before = await db.get(Candidate, cand_id)
        assert cand_before is not None
        assert str(cand_before.stage or "") == "contacted"
        await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        await db.commit()

    async with async_session_maker() as db:
        cand_after = await db.get(Candidate, cand_id)
        assert cand_after is not None
        assert str(cand_after.stage or "") == "contacted"


@pytest.mark.anyio
async def test_two_leads_same_candidate_two_application_rows(tenant_id: str) -> None:
    """§5 / §10: different ``lead_id`` → different intent rows (not idempotent with each other)."""
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_a = str(uuid.uuid4())
        lead_b = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Multi",
                last_name="Lead",
                email=f"multi-lead-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=vac_id,
            )
        )
        for lid in (lead_a, lead_b):
            db.add(
                Lead(
                    id=lid,
                    tenant_id=tenant_id,
                    lead_type="candidate",
                    company_id=company_id,
                    payload={},
                    normalized={},
                    status="processed",
                    candidate_id=cand_id,
                    vacancy_id=vac_id,
                    source="meta",
                )
            )
        await db.commit()

    async with async_session_maker() as db:
        a1 = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_a,
            vacancy_id=vac_id,
            source="meta",
        )
        a2 = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_b,
            vacancy_id=vac_id,
            source="meta",
        )
        assert a1 is not None and a2 is not None
        assert a1.id != a2.id
        await db.commit()

    async with async_session_maker() as db:
        cnt = await db.execute(
            select(func.count())
            .select_from(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.candidate_id == cand_id,
            )
        )
        assert int(cnt.scalar_one() or 0) == 2


@pytest.mark.anyio
async def test_pool_to_vacancy_updates_row_and_audit_meta(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Pool",
                last_name="Bind",
                email=f"pool-bind-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=None,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                lead_type="candidate",
                company_id=company_id,
                payload={},
                normalized={"recruitment_pool_intent_v1": True},
                status="processed",
                candidate_id=cand_id,
                vacancy_id=None,
                source="meta",
            )
        )
        await db.commit()

    async with async_session_maker() as db:
        app1 = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=None,
            source="meta",
        )
        assert app1 is not None
        assert app1.vacancy_id is None
        await db.commit()

    async with async_session_maker() as db:
        lead_row = await db.get(Lead, lead_id)
        assert lead_row is not None
        lead_row.vacancy_id = vac_id
        await db.flush()
        await db.commit()

    async with async_session_maker() as db:
        app2 = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        assert app2 is not None
        assert app2.id == app1.id
        assert app2.vacancy_id == vac_id
        meta = app2.meta if isinstance(app2.meta, dict) else {}
        trail = meta.get("pool_to_vacancy_audit_v1")
        assert isinstance(trail, list)
        assert len(trail) >= 1
        assert trail[-1].get("to_vacancy_id") == vac_id
        await db.commit()

