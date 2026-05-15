"""PR-1: tax / insurance / compliance rows exist after employee materialization (create + handoff)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models.workforce_compliance_state import WorkforceComplianceState
from backend.app.models.workforce_insurance_profile import WorkforceInsuranceProfile
from backend.app.models.workforce_tax_profile import WorkforceTaxProfile
from backend.app.services.workforce_hr_core_profiles import ensure_workforce_hr_core_profiles


async def _count_core_rows(tenant_id: str, employee_id: str) -> tuple[int, int, int]:
    async with async_session_maker() as session:
        tax_n = (
            await session.execute(
                select(func.count())
                .select_from(WorkforceTaxProfile)
                .where(
                    WorkforceTaxProfile.tenant_id == tenant_id,
                    WorkforceTaxProfile.employee_id == employee_id,
                )
            )
        ).scalar_one()
        ins_n = (
            await session.execute(
                select(func.count())
                .select_from(WorkforceInsuranceProfile)
                .where(
                    WorkforceInsuranceProfile.tenant_id == tenant_id,
                    WorkforceInsuranceProfile.employee_id == employee_id,
                )
            )
        ).scalar_one()
        comp_n = (
            await session.execute(
                select(func.count())
                .select_from(WorkforceComplianceState)
                .where(
                    WorkforceComplianceState.tenant_id == tenant_id,
                    WorkforceComplianceState.employee_id == employee_id,
                )
            )
        ).scalar_one()
    return int(tax_n or 0), int(ins_n or 0), int(comp_n or 0)


@pytest.mark.asyncio
async def test_hr_core_profiles_after_employee_create(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "HR core profiles create",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]
    tenant_id = bootstrap["tenant_id"]

    tax_n, ins_n, comp_n = await _count_core_rows(tenant_id, emp_id)
    assert tax_n == 1 and ins_n == 1 and comp_n == 1

    async with async_session_maker() as session:
        await ensure_workforce_hr_core_profiles(session, tenant_id, emp_id)
        await session.commit()
    tax_n2, ins_n2, comp_n2 = await _count_core_rows(tenant_id, emp_id)
    assert tax_n2 == 1 and ins_n2 == 1 and comp_n2 == 1


@pytest.mark.asyncio
async def test_hr_core_profiles_after_handoff_from_candidate(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    h = {**recruiter_headers, "Content-Type": "application/json"}
    resp = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=h,
        json={},
    )
    assert resp.status_code == 200, resp.text
    emp_id = resp.json()["id"]
    tenant_id = bootstrap["tenant_id"]

    tax_n, ins_n, comp_n = await _count_core_rows(tenant_id, emp_id)
    assert tax_n == 1 and ins_n == 1 and comp_n == 1
