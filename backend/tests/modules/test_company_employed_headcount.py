from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.vacancy import Vacancy
from backend.app.modules.companies.counters import (
    company_recruitment_metrics_for_list,
    get_company_counters,
)


def _uid() -> str:
    return str(uuid4())


@pytest.mark.anyio
async def test_company_counters_count_employed_stage_not_pipeline(db) -> None:
    tenant_id = str(db.info.get("tenant_id") or "")
    company_id = _uid()
    vacancy_id = _uid()

    db.add(
        Company(
            id=company_id,
            tenant_id=tenant_id,
            name="Rock Cargo employed count",
        )
    )
    db.add(
        Vacancy(
            id=vacancy_id,
            tenant_id=tenant_id,
            company_id=company_id,
            title="Kierowcy CE",
            employment_type="full_time",
            status="open",
        )
    )
    db.add(
        Candidate(
            id=_uid(),
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=vacancy_id,
            first_name="In",
            last_name="Pipeline",
            stage="contacted",
        )
    )
    db.add(
        Candidate(
            id=_uid(),
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=vacancy_id,
            first_name="Got",
            last_name="Job",
            stage="employed",
        )
    )
    db.add(
        Candidate(
            id=_uid(),
            tenant_id=tenant_id,
            company_id=company_id,
            vacancy_id=vacancy_id,
            first_name="Label",
            last_name="Employed",
            stage="Трудоустроен",
        )
    )
    await db.flush()

    counters = await get_company_counters(db, company_id)
    assert counters["candidates_total"] == 3
    assert counters["candidates_employed"] == 2

    metrics = await company_recruitment_metrics_for_list(
        db,
        tenant_id=tenant_id,
        company_ids=[company_id],
    )
    pack = metrics[company_id]
    assert pack["recruitment_candidates_total"] == 3
    assert pack["recruitment_candidates_employed"] == 2
