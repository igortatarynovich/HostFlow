"""Tests for recruitment funnel assignment helpers."""

from __future__ import annotations

import uuid

import pytest

from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.lead import Lead
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.services.recruitment_funnel_assignment import (
    assign_recruitment_funnel_to_lead,
    reconcile_candidate_funnel_on_company_change,
    reconcile_lead_funnel_on_company_change,
)


def _uid() -> str:
    return str(uuid.uuid4())


async def _seed_tenant(db) -> str:
    tid = _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"Assign Test {suffix}",
            slug=f"asg-{suffix}",
            api_key=f"asg-key-{suffix}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={"modules": {"recruitment": True, "candidates": True, "leads": True, "vacancies": True}},
        )
    )
    await db.flush()
    return tid


async def _seed_company(db, *, tenant_id: str, name_suffix: str = "A") -> str:
    cid = _uid()
    db.add(Company(id=cid, tenant_id=tenant_id, name=f"Co {name_suffix} {cid[:8]}"))
    await db.flush()
    return cid


async def _seed_funnel(
    db,
    *,
    tenant_id: str,
    company_id: str,
    funnel_type: str = "candidate",
    name: str = "Default",
) -> Funnel:
    funnel = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key="recruitment",
        type=funnel_type,
        name=name,
        is_default=True,
    )
    db.add(funnel)
    await db.flush()
    return funnel


@pytest.mark.anyio
async def test_reconcile_candidate_funnel_on_company_change(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_a = await _seed_company(db, tenant_id=tenant_id, name_suffix="A")
    company_b = await _seed_company(db, tenant_id=tenant_id, name_suffix="B")
    funnel_a = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_a, name="A Pipeline")
    funnel_b = await _seed_funnel(db, tenant_id=tenant_id, company_id=company_b, name="B Pipeline")

    candidate = Candidate(
        id=_uid(),
        tenant_id=tenant_id,
        first_name="Test",
        last_name="User",
        company_id=company_a,
        funnel_id=funnel_a.id,
        stage="new",
        status="new",
    )
    db.add(candidate)
    await db.flush()

    changes: dict = {"company_id": company_b}
    await reconcile_candidate_funnel_on_company_change(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
        new_company_id=company_b,
        changes=changes,
    )

    assert changes["funnel_id"] == funnel_b.id


@pytest.mark.anyio
async def test_assign_recruitment_funnel_to_lead(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    lead_funnel = await _seed_funnel(
        db, tenant_id=tenant_id, company_id=company_id, funnel_type="lead", name="Lead Pipeline"
    )

    lead = Lead(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        lead_type="candidate",
        lead_target_type="candidate",
        source="manual",
        status="new",
        stage="new",
    )
    db.add(lead)
    await db.flush()

    result = await assign_recruitment_funnel_to_lead(
        db, tenant_id=tenant_id, lead=lead, pipeline_type="lead"
    )

    assert result is not None
    assert lead.funnel_id == lead_funnel.id


@pytest.mark.anyio
async def test_reconcile_lead_funnel_on_company_change(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_a = await _seed_company(db, tenant_id=tenant_id, name_suffix="A")
    company_b = await _seed_company(db, tenant_id=tenant_id, name_suffix="B")
    funnel_a = await _seed_funnel(
        db, tenant_id=tenant_id, company_id=company_a, funnel_type="lead", name="Lead A"
    )
    await _seed_funnel(
        db, tenant_id=tenant_id, company_id=company_b, funnel_type="lead", name="Lead B"
    )

    lead = Lead(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_a,
        funnel_id=funnel_a.id,
        lead_type="candidate",
        lead_target_type="candidate",
        source="manual",
        status="new",
        stage="new",
    )
    db.add(lead)
    await db.flush()

    await reconcile_lead_funnel_on_company_change(
        db,
        tenant_id=tenant_id,
        lead=lead,
        old_company_id=company_a,
        new_company_id=company_b,
    )

    assert lead.funnel_id != funnel_a.id
    assert lead.funnel_id is not None
