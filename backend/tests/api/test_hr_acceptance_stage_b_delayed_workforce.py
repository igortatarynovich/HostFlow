"""Stage B: delayed workforce creation — accept handoff without employee until employment approve."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models.document_entity_link import DocumentEntityLink
from backend.app.models.tenant import Tenant
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_review import WorkforceHrReview
from backend.app.models.workforce_onboarding_task import WorkforceOnboardingTask
from backend.app.models.workforce_work_eligibility_profile import WorkforceWorkEligibilityProfile
from backend.tests.test_support.candidate_evidence_helpers import close_driver_ce_requirements
from backend.tests.test_support.hr_verification_e2e import prepare_handoff_hr_review_for_approve
from backend.app.models.workforce_zus_profile import WorkforceZusProfile
from backend.tests.api.test_handoff_internal_hr import (
    _ensure_hr_employee_funnel_for_company,
    _ensure_tenant_link_internal_hr,
)
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


async def _set_delayed_hr_workforce_creation(tenant_id: str, *, enabled: bool) -> None:
    from sqlalchemy.orm.attributes import flag_modified

    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        assert tenant is not None
        settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
        if enabled:
            settings["delayed_hr_workforce_creation"] = True
        else:
            settings.pop("delayed_hr_workforce_creation", None)
        tenant.settings = settings
        flag_modified(tenant, "settings")
        await session.commit()


async def _count_employees_for_candidate(tenant_id: str, candidate_id: str) -> int:
    async with async_session_maker() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(WorkforceEmployee)
                    .where(
                        WorkforceEmployee.tenant_id == tenant_id,
                        WorkforceEmployee.candidate_id == candidate_id,
                    )
                )
            ).scalar_one()
            or 0
        )


async def _review_for_handoff(tenant_id: str, handoff_id: str) -> WorkforceHrReview | None:
    async with async_session_maker() as session:
        return (
            await session.execute(
                select(WorkforceHrReview).where(
                    WorkforceHrReview.tenant_id == tenant_id,
                    WorkforceHrReview.handoff_id == handoff_id,
                )
            )
        ).scalar_one_or_none()


async def _onboarding_task_count(tenant_id: str, employee_id: str) -> int:
    async with async_session_maker() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(WorkforceOnboardingTask)
                    .where(
                        WorkforceOnboardingTask.tenant_id == tenant_id,
                        WorkforceOnboardingTask.employee_id == employee_id,
                    )
                )
            ).scalar_one()
            or 0
        )


async def _has_zus_profile(tenant_id: str, employee_id: str) -> bool:
    async with async_session_maker() as session:
        return (
            await session.execute(
                select(func.count())
                .select_from(WorkforceZusProfile)
                .where(
                    WorkforceZusProfile.tenant_id == tenant_id,
                    WorkforceZusProfile.employee_id == employee_id,
                )
            )
        ).scalar_one() > 0


async def _count_doc_links(
    tenant_id: str, *, linked_entity_type: str, linked_entity_id: str
) -> int:
    async with async_session_maker() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(DocumentEntityLink)
                    .where(
                        DocumentEntityLink.tenant_id == tenant_id,
                        DocumentEntityLink.linked_entity_type == linked_entity_type,
                        DocumentEntityLink.linked_entity_id == linked_entity_id,
                        DocumentEntityLink.relation_type == "reused_for_hr",
                    )
                )
            ).scalar_one()
            or 0
        )


async def _work_eligibility_row(
    tenant_id: str, employee_id: str
) -> WorkforceWorkEligibilityProfile | None:
    async with async_session_maker() as session:
        return (
            await session.execute(
                select(WorkforceWorkEligibilityProfile).where(
                    WorkforceWorkEligibilityProfile.tenant_id == tenant_id,
                    WorkforceWorkEligibilityProfile.employee_id == employee_id,
                )
            )
        ).scalar_one_or_none()


@pytest.mark.anyio
async def test_delayed_workforce_accept_then_approve_creates_employee_and_hr_bundle(
    client: AsyncClient,
    recruiter_headers: dict,
    hr_officer_headers: dict,
    manager_headers: dict,
    candidate_id: str,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _set_delayed_hr_workforce_creation(tenant_id, enabled=True)
    try:
        await _run_delayed_workforce_flow(
            client,
            recruiter_headers=recruiter_headers,
            hr_officer_headers=hr_officer_headers,
            manager_headers=manager_headers,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            company_id=company_id,
        )
    finally:
        await _set_delayed_hr_workforce_creation(tenant_id, enabled=False)


async def _run_delayed_workforce_flow(
    client: AsyncClient,
    *,
    recruiter_headers: dict,
    hr_officer_headers: dict,
    manager_headers: dict,
    candidate_id: str,
    tenant_id: str,
    company_id: str,
) -> None:
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await _ensure_hr_employee_funnel_for_company(tenant_id=tenant_id, company_id=company_id)
    await close_driver_ce_requirements(
        client, manager_headers, candidate_id=candidate_id
    )

    rf = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"stage": "ready_for_handoff"},
    )
    assert rf.status_code == 200, rf.text
    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    handoff_id = ho.json()["id"]

    acc = await client.post(f"/api/v1/handoffs/{handoff_id}/accept", headers=hr_officer_headers)
    assert acc.status_code == 200, acc.text

    assert await _count_employees_for_candidate(tenant_id, candidate_id) == 0

    review_row = await _review_for_handoff(tenant_id, handoff_id)
    assert review_row is not None
    assert review_row.status in (
        "hr_review_in_progress",
        "waiting_documents",
        "waiting_payments",
        "waiting_work_permit",
        "waiting_red_paper",
    )
    assert await _count_doc_links(
        tenant_id,
        linked_entity_type="workforce_hr_review",
        linked_entity_id=str(review_row.id),
    ) >= 1

    handoff_review = await client.get(
        f"/api/v1/handoffs/{handoff_id}/hr-review",
        headers=hr_officer_headers,
    )
    assert handoff_review.status_code == 200, handoff_review.text
    panel = handoff_review.json()
    assert panel.get("handoff_id") == handoff_id
    assert panel.get("employee_id") in (None, "")
    docs = panel.get("documents_for_approval") or []
    assert any(str(d.get("document_id") or "").strip() for d in docs if isinstance(d, dict))

    assert len(panel.get("checklist") or []) >= 1

    await prepare_handoff_hr_review_for_approve(client, handoff_id, hr_officer_headers)

    approve = await client.post(
        f"/api/v1/handoffs/{handoff_id}/hr-review/approve",
        headers=hr_officer_headers,
    )
    assert approve.status_code == 200, approve.text
    approved = approve.json()
    emp_id = str(approved.get("employee_id") or "")
    assert emp_id

    assert await _count_employees_for_candidate(tenant_id, candidate_id) == 1
    assert await _onboarding_task_count(tenant_id, emp_id) > 0
    assert await _has_zus_profile(tenant_id, emp_id)
    assert await _count_doc_links(
        tenant_id,
        linked_entity_type="workforce_employee",
        linked_entity_id=emp_id,
    ) >= 1

    review_after = await _review_for_handoff(tenant_id, handoff_id)
    assert review_after is not None
    assert review_after.status == "approved_for_employment"
    assert str(review_after.employee_id) == emp_id

    emp_list = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert emp_list.status_code == 200, emp_list.text
    matched = [e for e in emp_list.json() if str(e.get("id")) == emp_id]
    assert matched
    snap = matched[0].get("candidate_snapshot") or {}
    assert isinstance(snap.get("personal_data"), dict)
    assert isinstance(snap.get("extra"), dict)
    assert snap.get("document_field_values") is not None

    wel = await _work_eligibility_row(tenant_id, emp_id)
    assert wel is not None
    assert wel.citizenship == "UA"
    assert wel.work_country == "PL"

    emp_detail = await client.get(
        f"/api/v1/workforce/employees/{emp_id}",
        headers=hr_officer_headers,
    )
    assert emp_detail.status_code == 200, emp_detail.text
    pipeline = (emp_detail.json().get("meta") or {}).get("employee_pipeline") or {}
    assert pipeline.get("funnel_id")
    assert pipeline.get("stage_code")
    assert pipeline.get("origin") == "recruitment_handoff"
