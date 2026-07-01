"""ZUS workspace auto-create: registration, deregistration, monthly (idempotent)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.jobs.zus_workspace_monthly_cycle import run_monthly_zus_workspace_for_tenant
from backend.app.models.audit import ActivityLog
from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask
from backend.app.services.workforce_zus_task_autocreate import (
    TASK_KIND_DEREGISTRATION,
    TASK_KIND_MONTHLY_SETTLEMENT,
    TASK_KIND_REGISTRATION,
    ensure_zus_registration_task,
)


async def _count_tasks(
    tenant_id: str, employee_id: str, *, task_kind: str, form_kind: str | None = None
) -> int:
    async with async_session_maker() as session:
        q = select(func.count()).select_from(WorkforceZusWorkspaceTask).where(
            WorkforceZusWorkspaceTask.tenant_id == tenant_id,
            WorkforceZusWorkspaceTask.employee_id == employee_id,
            WorkforceZusWorkspaceTask.task_kind == task_kind,
        )
        if form_kind is not None:
            q = q.where(WorkforceZusWorkspaceTask.form_kind == form_kind)
        c = (await session.execute(q)).scalar_one()
    return int(c or 0)


async def _latest_registration_task(
    tenant_id: str, employee_id: str, *, form_kind: str
) -> WorkforceZusWorkspaceTask | None:
    async with async_session_maker() as session:
        return (
            await session.execute(
                select(WorkforceZusWorkspaceTask)
                .where(
                    WorkforceZusWorkspaceTask.tenant_id == tenant_id,
                    WorkforceZusWorkspaceTask.employee_id == employee_id,
                    WorkforceZusWorkspaceTask.task_kind == TASK_KIND_REGISTRATION,
                    WorkforceZusWorkspaceTask.form_kind == form_kind,
                )
                .order_by(WorkforceZusWorkspaceTask.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()


async def _latest_auto_log(tenant_id: str, employee_id: str) -> ActivityLog | None:
    async with async_session_maker() as session:
        rows = (
            (
                await session.execute(
                    select(ActivityLog)
                    .where(
                        ActivityLog.tenant_id == tenant_id,
                        ActivityLog.action == "zus_task_auto_created",
                    )
                    .order_by(ActivityLog.created_at.desc())
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )
    for r in rows:
        p = r.payload or {}
        if str(p.get("employee_id") or "") == str(employee_id):
            return r
    return None


@pytest.mark.asyncio
async def test_employee_create_with_insurance_seeds_registration_task(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "ZUS autocreate on hire",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
            "initial_insurance_zus_registration_type": "umowa_o_pracy",
            "initial_insurance_status": "pending_registration",
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]
    tid = bootstrap["tenant_id"]
    assert await _count_tasks(tid, emp_id, task_kind=TASK_KIND_REGISTRATION, form_kind="ZUA") == 1
    reg = await _latest_registration_task(tid, emp_id, form_kind="ZUA")
    assert reg is not None
    assert reg.status == "pending"
    log = await _latest_auto_log(tid, emp_id)
    assert log is not None
    p = log.payload or {}
    assert p.get("task_kind") == TASK_KIND_REGISTRATION
    assert p.get("form_kind") == "ZUA"
    assert p.get("task_id")
    assert "actor_id" in p


@pytest.mark.asyncio
async def test_repeat_ensure_registration_no_duplicate(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "ZUS ensure idempotent",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
            "initial_insurance_zus_registration_type": "umowa_zlecenia",
            "initial_insurance_status": "pending_zus",
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]
    tid = bootstrap["tenant_id"]
    assert await _count_tasks(tid, emp_id, task_kind=TASK_KIND_REGISTRATION, form_kind="ZZA") == 1
    reg = await _latest_registration_task(tid, emp_id, form_kind="ZZA")
    assert reg is not None
    assert reg.status == "pending"

    async with async_session_maker() as db:
        await ensure_zus_registration_task(db, emp_id, source="test")
        await ensure_zus_registration_task(db, emp_id, source="test")
        await db.commit()

    assert await _count_tasks(tid, emp_id, task_kind=TASK_KIND_REGISTRATION, form_kind="ZZA") == 1


@pytest.mark.asyncio
async def test_insurance_patch_deregistered_at_creates_zwua(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "ZUS ZWUA from insurance",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]
    tid = bootstrap["tenant_id"]

    patch = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/insurance-profile",
        headers=h,
        json={"deregistered_at": "2026-04-10"},
    )
    assert patch.status_code == 200, patch.text
    assert await _count_tasks(tid, emp_id, task_kind=TASK_KIND_DEREGISTRATION, form_kind="ZWUA") == 1

    patch2 = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/insurance-profile",
        headers=h,
        json={"deregistered_at": "2026-04-10"},
    )
    assert patch2.status_code == 200, patch2.text
    assert await _count_tasks(tid, emp_id, task_kind=TASK_KIND_DEREGISTRATION, form_kind="ZWUA") == 1


@pytest.mark.asyncio
async def test_monthly_job_creates_then_idempotent(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "ZUS monthly subject",
            "status": "active",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]
    tid = bootstrap["tenant_id"]
    period = "2099-07"

    s1 = await run_monthly_zus_workspace_for_tenant(
        tenant_id=tid,
        period_yyyy_mm=period,
        dry_run=False,
    )
    assert s1.get("tasks_created", 0) >= 1
    assert (
        await _count_tasks(
            tid,
            emp_id,
            task_kind=TASK_KIND_MONTHLY_SETTLEMENT,
            form_kind="monthly_settlement",
        )
        == 1
    )

    s2 = await run_monthly_zus_workspace_for_tenant(
        tenant_id=tid,
        period_yyyy_mm=period,
        dry_run=False,
    )
    assert (
        await _count_tasks(
            tid,
            emp_id,
            task_kind=TASK_KIND_MONTHLY_SETTLEMENT,
            form_kind="monthly_settlement",
        )
        == 1
    )
    assert s2.get("tasks_created", 0) == 0


@pytest.mark.asyncio
async def test_registration_blocked_for_third_country_driver_until_ready_for_zus(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    """Foreign driver + not_evaluated blocks ZUS registration until eligibility is ready_for_zus."""
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "ZUS gated driver",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]
    tid = bootstrap["tenant_id"]

    wel = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/work-eligibility",
        headers=h,
        json={
            "position_category": "driver",
            "citizenship": "UA",
            "requires_work_permit": True,
        },
    )
    assert wel.status_code == 200, wel.text

    ins = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/insurance-profile",
        headers=h,
        json={
            "zus_registration_type": "umowa_o_pracy",
            "status": "pending_registration",
        },
    )
    assert ins.status_code == 200, ins.text

    assert await _count_tasks(tid, emp_id, task_kind=TASK_KIND_REGISTRATION, form_kind="ZUA") == 1
    reg_blocked = await _latest_registration_task(tid, emp_id, form_kind="ZUA")
    assert reg_blocked is not None
    assert reg_blocked.status == "blocked"
    ch = reg_blocked.checklist_json or {}
    bb = set(ch.get("blocked_by") or [])
    assert "legal_stay" in bb and "work_permit" in bb
    assert "work_permit_fee" in bb and "red_paper_fee" in bb

    prof = await client.get(f"/api/v1/workforce/employees/{emp_id}/operational-profile", headers=hr_officer_headers)
    assert prof.status_code == 200, prof.text
    pay_rows = (prof.json().get("hr_bundle") or {}).get("work_eligibility_payment_requirements") or []
    by_type = {r["requirement_type"]: r["id"] for r in pay_rows}
    assert "work_permit_fee" in by_type and "red_paper_fee" in by_type

    for rt in ("work_permit_fee", "red_paper_fee"):
        pr = await client.patch(
            f"/api/v1/workforce/employees/{emp_id}/work-eligibility/payment-requirements/{by_type[rt]}",
            headers=h,
            json={"payment_status": "paid", "payment_reference": f"ref-{rt}"},
        )
        assert pr.status_code == 200, pr.text

    unblocked = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/work-eligibility",
        headers=h,
        json={"eligibility_status": "ready_for_zus"},
    )
    assert unblocked.status_code == 200, unblocked.text

    reg_ready = await _latest_registration_task(tid, emp_id, form_kind="ZUA")
    assert reg_ready is not None
    assert reg_ready.id == reg_blocked.id
    assert reg_ready.status == "pending"
    ch2 = reg_ready.checklist_json or {}
    assert "blocked_by" not in ch2


@pytest.mark.asyncio
async def test_reject_work_permit_submitted_without_fee_paid(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "fee gate submit",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    wel = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/work-eligibility",
        headers=h,
        json={
            "position_category": "driver",
            "citizenship": "UA",
            "requires_work_permit": True,
        },
    )
    assert wel.status_code == 200, wel.text

    bad = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/work-eligibility",
        headers=h,
        json={"work_permit_application_status": "submitted"},
    )
    assert bad.status_code == 400, bad.text
