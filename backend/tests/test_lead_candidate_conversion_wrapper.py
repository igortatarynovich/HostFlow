"""Conversion wrapper v1: audit + idempotent return when lead already links a dossier."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.models import ActivityLog, Candidate, Company, Lead, OwnCompany, Vacancy
from backend.app.modules.leads.lead_candidate_conversion import (
    CONVERSION_CONTRACT_VERSION,
    create_candidate_from_lead_conversion,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_conversion_idempotent_when_lead_already_has_candidate_id(db):
    """Re-processing must not INSERT a second Candidate if the lead row already links one."""
    oc = OwnCompany(id=str(uuid.uuid4()), tenant_id=TENANT_ID, name="OC Conversion Idemp")
    db.add(oc)
    await db.flush()

    company_id = (
        await db.execute(select(Company.id).where(Company.tenant_id == TENANT_ID).limit(1))
    ).scalar_one()

    vacancy = Vacancy(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        company_id=str(company_id),
        own_company_id=oc.id,
        title="Vacancy conversion idemp",
        status="open",
        is_active=True,
        is_archived=False,
    )
    db.add(vacancy)
    await db.flush()

    cand = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        own_company_id=oc.id,
        first_name="Existing",
        last_name="Dossier",
        company_id=str(company_id),
        vacancy_id=vacancy.id,
        stage="docs_wait",
        status="docs_wait",
    )
    db.add(cand)
    await db.flush()

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=TENANT_ID,
        own_company_id=oc.id,
        lead_type="candidate",
        company_id=str(company_id),
        vacancy_id=vacancy.id,
        payload={},
        normalized={"email": "idemp-wrapper@test.local"},
        status="new",
        source="meta",
        external_id=f"idemp-ext-{uuid.uuid4().hex}",
        candidate_id=cand.id,
    )
    db.add(lead)
    await db.flush()

    n_before = (
        await db.execute(select(func.count()).select_from(Candidate).where(Candidate.tenant_id == TENANT_ID))
    ).scalar_one()

    payload = {
        "first_name": "Would",
        "last_name": "Duplicate",
        "email": "other@test.local",
        "own_company_id": oc.id,
        "company_id": str(company_id),
        "vacancy_id": vacancy.id,
        "source": "meta",
        "origin": {"meta": {}},
    }
    out = await create_candidate_from_lead_conversion(
        db,
        tenant_id=TENANT_ID,
        lead=lead,
        candidate_payload=payload,
        source_channel="meta",
        duplicate_match_level="none",
        conversion_reason="lead_processing",
    )
    await db.commit()

    assert str(out.id) == cand.id
    n_after = (
        await db.execute(select(func.count()).select_from(Candidate).where(Candidate.tenant_id == TENANT_ID))
    ).scalar_one()
    assert n_after == n_before

    row = (
        await db.execute(
            select(ActivityLog)
            .where(
                ActivityLog.tenant_id == TENANT_ID,
                ActivityLog.action == "candidate_created",
                ActivityLog.target_id == cand.id,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one()
    assert row.payload.get("conversion_contract_version") == CONVERSION_CONTRACT_VERSION
    assert row.payload.get("idempotent_replay") is True
    assert row.payload.get("source_lead_id") == str(lead.id)
    assert row.payload.get("external_id") == lead.external_id
    assert row.payload.get("duplicate_result") == "no_duplicate"
