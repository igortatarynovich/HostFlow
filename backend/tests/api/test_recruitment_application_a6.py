"""A6 — Application lifecycle: C2b external idempotency, I1 vacancy switch, C3 hired guard."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services.recruitment_application_lifecycle import InvalidRecruitmentApplicationTransition
from backend.app.services.recruitment_application_service import (
    ensure_recruitment_application_for_external_intent,
    ensure_recruitment_application_for_lead_intent,
    patch_recruitment_application_status,
    switch_recruitment_application_vacancy,
)
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


@pytest.mark.anyio
async def test_c2b_external_idempotent_and_second_apply_new_cycle(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Portal",
                last_name="Repeat",
                email=f"portal-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=vac_id,
            )
        )
        await db.commit()

    ext_a = f"portal-event-{uuid.uuid4().hex[:12]}"
    ext_b = f"portal-event-{uuid.uuid4().hex[:12]}"

    async with async_session_maker() as db:
        a1 = await ensure_recruitment_application_for_external_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            external_id=ext_a,
            source="public_intake",
            vacancy_id=vac_id,
        )
        assert a1 is not None
        assert a1.application_cycle == "cycle-1"
        assert a1.external_id == ext_a
        a1b = await ensure_recruitment_application_for_external_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            external_id=ext_a,
            source="public_intake",
            vacancy_id=vac_id,
        )
        assert a1b is not None
        assert a1b.id == a1.id
        a2 = await ensure_recruitment_application_for_external_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            external_id=ext_b,
            source="public_intake",
            vacancy_id=vac_id,
        )
        assert a2 is not None
        assert a2.id != a1.id
        assert a2.application_cycle == "cycle-2"
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
async def test_i1_vacancy_switch_creates_new_row_and_withdraws_progressed(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_a = await _ensure_vacancy(db, tenant_id, company_id)
        vac_b = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Switch",
                last_name="Vac",
                email=f"switch-{uuid.uuid4().hex[:10]}@example.com",
                stage="new",
                status="new",
                company_id=company_id,
                vacancy_id=vac_a,
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
                vacancy_id=vac_a,
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
            vacancy_id=vac_a,
            source="meta",
        )
        assert app is not None
        await patch_recruitment_application_status(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            application_id=str(app.id),
            new_status="in_review",
        )
        await db.commit()
        app_id = str(app.id)

    async with async_session_maker() as db:
        prev, new_app = await switch_recruitment_application_vacancy(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            application_id=app_id,
            to_vacancy_id=vac_b,
            close_previous=True,
        )
        assert new_app.id != prev.id
        assert new_app.vacancy_id == vac_b
        assert new_app.status == "applied"
        assert prev.vacancy_id == vac_a
        assert prev.status == "withdrawn"
        meta = new_app.meta if isinstance(new_app.meta, dict) else {}
        assert isinstance(meta.get("vacancy_switch_audit_v1"), list)
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
async def test_c3_hired_status_does_not_create_workforce_employee(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Hire",
                last_name="OnlyApp",
                email=f"hire-{uuid.uuid4().hex[:10]}@example.com",
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
        app = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        assert app is not None
        app_id = str(app.id)
        await patch_recruitment_application_status(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            application_id=app_id,
            new_status="hired",
        )
        await db.commit()

    async with async_session_maker() as db:
        emp_cnt = await db.execute(
            select(func.count())
            .select_from(WorkforceEmployee)
            .where(
                WorkforceEmployee.tenant_id == tenant_id,
                WorkforceEmployee.candidate_id == cand_id,
            )
        )
        assert int(emp_cnt.scalar_one() or 0) == 0


@pytest.mark.anyio
async def test_patch_application_status_api_hired_no_employee(
    client: AsyncClient,
    manager_headers: dict,
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Api",
                last_name="Hired",
                email=f"api-hire-{uuid.uuid4().hex[:10]}@example.com",
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
        app = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        assert app is not None
        app_id = str(app.id)
        await db.commit()

    r = await client.patch(
        f"/api/v1/candidates/{cand_id}/applications/{app_id}",
        headers=manager_headers,
        json={"status": "hired"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "hired"

    async with async_session_maker() as db:
        emp_cnt = await db.execute(
            select(func.count())
            .select_from(WorkforceEmployee)
            .where(
                WorkforceEmployee.tenant_id == tenant_id,
                WorkforceEmployee.candidate_id == cand_id,
            )
        )
        assert int(emp_cnt.scalar_one() or 0) == 0


@pytest.mark.anyio
async def test_patch_application_status_rejects_invalid_transition(tenant_id: str) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        vac_id = await _ensure_vacancy(db, tenant_id, company_id)
        cand_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        db.add(
            Candidate(
                id=cand_id,
                tenant_id=tenant_id,
                first_name="Bad",
                last_name="Trans",
                email=f"bad-{uuid.uuid4().hex[:10]}@example.com",
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
        app = await ensure_recruitment_application_for_lead_intent(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            lead_id=lead_id,
            vacancy_id=vac_id,
            source="meta",
        )
        assert app is not None
        await patch_recruitment_application_status(
            db,
            tenant_id=tenant_id,
            candidate_id=cand_id,
            application_id=str(app.id),
            new_status="rejected",
        )
        with pytest.raises(InvalidRecruitmentApplicationTransition):
            await patch_recruitment_application_status(
                db,
                tenant_id=tenant_id,
                candidate_id=cand_id,
                application_id=str(app.id),
                new_status="hired",
            )
        await db.rollback()
