"""B2-G4 — idempotency and repeat handoff pipeline meta policy (§5.3)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.tests.api.test_handoff_internal_hr import (
    _ensure_hr_employee_funnel_for_company,
    _ensure_tenant_link_internal_hr,
    internal_hr_handoff_create_and_accept,
)
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


pytestmark = pytest.mark.anyio


async def _count_employees(tenant_id: str, candidate_id: str) -> int:
    async with async_session_maker() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(WorkforceEmployee)
                    .where(
                        WorkforceEmployee.tenant_id == tenant_id,
                        WorkforceEmployee.candidate_id == candidate_id,
                        WorkforceEmployee.status.notin_(("returned_to_recruitment", "returned", "terminated")),
                    )
                )
            ).scalar_one()
            or 0
        )


async def _ensure_delayed_workforce_disabled(tenant_id: str) -> None:
    from sqlalchemy.orm.attributes import flag_modified

    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        assert tenant is not None
        settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
        settings.pop("delayed_hr_workforce_creation", None)
        tenant.settings = settings
        flag_modified(tenant, "settings")
        await session.commit()


async def test_repeat_from_candidate_is_idempotent(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_delayed_workforce_disabled(tenant_id)
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await _ensure_hr_employee_funnel_for_company(tenant_id=tenant_id, company_id=company_id)
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
        tenant_id=tenant_id,
    )
    assert await _count_employees(tenant_id, candidate_id) == 1

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst.status_code == 200, lst.text
    emp_id = next(
        str(row["id"]) for row in lst.json() if str(row.get("candidate_id") or "") == candidate_id
    )

    repeat = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=recruiter_headers,
        json={},
    )
    assert repeat.status_code == 200, repeat.text
    assert str(repeat.json().get("id") or "") == emp_id
    assert await _count_employees(tenant_id, candidate_id) == 1


async def test_repeat_from_candidate_preserves_advanced_pipeline_stage(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_delayed_workforce_disabled(tenant_id)
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await _ensure_hr_employee_funnel_for_company(tenant_id=tenant_id, company_id=company_id)
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
        tenant_id=tenant_id,
    )

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    emp_id = next(
        str(row["id"]) for row in lst.json() if str(row.get("candidate_id") or "") == candidate_id
    )

    async with async_session_maker() as session:
        emp = await session.get(WorkforceEmployee, emp_id)
        assert emp is not None
        meta = dict(emp.meta or {})
        pipeline = dict(meta.get("employee_pipeline") or {})
        pipeline["stage_code"] = "verification"
        meta["employee_pipeline"] = pipeline
        emp.meta = meta
        await session.commit()

    repeat = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=recruiter_headers,
        json={},
    )
    assert repeat.status_code == 200, repeat.text

    detail = await client.get(
        f"/api/v1/workforce/employees/{emp_id}",
        headers=hr_officer_headers,
    )
    assert detail.status_code == 200, detail.text
    stage = ((detail.json().get("meta") or {}).get("employee_pipeline") or {}).get("stage_code")
    assert stage == "verification"
