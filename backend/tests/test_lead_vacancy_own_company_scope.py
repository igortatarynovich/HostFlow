"""§2.4: vacancy metadata + fit-check must not leak across own_company_id."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from backend.app.models import Company, Lead, OwnCompany, Vacancy
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.leads import service as leads_service

TENANT_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_list_leads_outerjoin_vacancy_requires_own_company_alignment(db):
    oc_a = OwnCompany(id=str(uuid.uuid4()), tenant_id=TENANT_ID, name="OC A Scope Test")
    oc_b = OwnCompany(id=str(uuid.uuid4()), tenant_id=TENANT_ID, name="OC B Scope Test")
    db.add_all([oc_a, oc_b])
    await db.flush()

    company_id = (
        await db.execute(select(Company.id).where(Company.tenant_id == TENANT_ID).limit(1))
    ).scalar_one()

    criteria = {"min_experience_eu_years": 99}
    v_extra = json.dumps({"lead_criteria_v1": criteria}, separators=(",", ":"))
    v_b = Vacancy(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        company_id=str(company_id),
        own_company_id=oc_b.id,
        title="Vacancy in workspace B",
        extra=v_extra,
    )
    db.add(v_b)
    await db.flush()

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        own_company_id=oc_a.id,
        lead_type="candidate",
        company_id=str(company_id),
        vacancy_id=v_b.id,
        payload={},
        normalized={"experience_eu_years": 0},
        status="new",
    )
    db.add(lead)
    await db.flush()

    resp = await leads_service.list_leads(
        db,
        tenant_id=TENANT_ID,
        own_company_id=oc_a.id,
        limit=100,
        offset=0,
    )
    item = next((x for x in resp.items if str(x.id) == lead.id), None)
    assert item is not None
    assert item.vacancy_title is None
    assert item.fit_status == "no_criteria"


@pytest.mark.asyncio
async def test_resolve_vacancy_by_id_scoped_own_company(db):
    oc_a = OwnCompany(id=str(uuid.uuid4()), tenant_id=TENANT_ID, name="OC A Resolve Test")
    oc_b = OwnCompany(id=str(uuid.uuid4()), tenant_id=TENANT_ID, name="OC B Resolve Test")
    db.add_all([oc_a, oc_b])
    await db.flush()

    company_id = (
        await db.execute(select(Company.id).where(Company.tenant_id == TENANT_ID).limit(1))
    ).scalar_one()

    v_b = Vacancy(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        company_id=str(company_id),
        own_company_id=oc_b.id,
        title="Scoped vacancy B",
        extra=None,
    )
    db.add(v_b)
    await db.flush()

    assert (
        await leads_crud.resolve_vacancy_by_id(
            db, TENANT_ID, v_b.id, scoped_own_company_id=oc_a.id
        )
        is None
    )
    assert (
        await leads_crud.resolve_vacancy_by_id(
            db, TENANT_ID, v_b.id, scoped_own_company_id=oc_b.id
        )
        is not None
    )
    assert await leads_crud.resolve_vacancy_by_id(db, TENANT_ID, v_b.id) is not None

    v_global = Vacancy(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        company_id=str(company_id),
        own_company_id=None,
        title="Legacy tenant-wide vacancy",
        extra=None,
    )
    db.add(v_global)
    await db.flush()

    assert (
        await leads_crud.resolve_vacancy_by_id(
            db, TENANT_ID, v_global.id, scoped_own_company_id=oc_a.id
        )
        is not None
    )
