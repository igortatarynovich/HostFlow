"""PR15 — hybrid HR approve readiness (plan-only gate + approve API alignment)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.hr_verification_e2e import (
    confirm_all_blocking_documents,
    fetch_hr_panel,
    plan_from_panel,
    setup_hr_review_case,
)


@pytest.mark.anyio
async def test_hybrid_ready_plan_approve_returns_200(
    client: AsyncClient,
    recruiter_headers: dict,
    hr_officer_headers: dict,
    manager_headers: dict,
    candidate_id: str,
    bootstrap: dict,
) -> None:
    emp_id = await setup_hr_review_case(
        client,
        manager_headers=manager_headers,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        bootstrap=bootstrap,
        citizenship="PL",
        position_category="warehouse",
    )
    panel = await confirm_all_blocking_documents(client, emp_id, hr_officer_headers)
    plan = plan_from_panel(panel)
    assert plan.get("plan_mode") == "hybrid"
    assert plan.get("can_approve") is True
    assert panel.get("can_approve") is True

    approved = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/approve",
        headers=hr_officer_headers,
    )
    assert approved.status_code == 200, approved.text


@pytest.mark.anyio
async def test_hybrid_blocked_plan_approve_returns_422(
    client: AsyncClient,
    recruiter_headers: dict,
    hr_officer_headers: dict,
    manager_headers: dict,
    candidate_id: str,
    bootstrap: dict,
) -> None:
    emp_id = await setup_hr_review_case(
        client,
        manager_headers=manager_headers,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        bootstrap=bootstrap,
        citizenship="PL",
        position_category="warehouse",
    )
    panel = await fetch_hr_panel(client, emp_id, hr_officer_headers)
    plan = plan_from_panel(panel)
    assert plan.get("plan_mode") == "hybrid"
    assert plan.get("can_approve") is False
    assert plan.get("blocking_reasons")

    blocked = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/approve",
        headers=hr_officer_headers,
    )
    assert blocked.status_code == 422, blocked.text
    detail = blocked.json().get("detail") or {}
    assert detail.get("code") == "HR_REVIEW_BLOCKED"
