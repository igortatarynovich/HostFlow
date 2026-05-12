"""Smoke tests aligned with docs/hr/module-scope.md — «Критерии готовности v0».

После handoff из кандидата: auto-bundle (вопросы 1, 3, 4, 5), доступ к досье по кандидату (вопрос 2, MVP).
"""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

from backend.app.services.workforce_employees import DEFAULT_ONBOARDING_TASK_TITLES


@pytest.mark.asyncio
async def test_handoff_hr_bundle_seeds_employment_payroll_zus_onboarding(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    """Вопросы 1 / 3 / 5 (MVP): есть employment, payroll-профиль, ZUS-профиль; вопрос 4 — задачи онбординга."""
    h = {**recruiter_headers, "Content-Type": "application/json"}
    handoff = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=h,
        json={},
    )
    assert handoff.status_code == 200, handoff.text
    emp_id = handoff.json()["id"]

    res = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/hr-bundle",
        headers=recruiter_headers,
    )
    assert res.status_code == 200, res.text
    b = res.json()

    assert len(b["employments"]) >= 1
    assert b["employments"][0].get("contract_type") == "unknown"

    assert b["payroll_profile"] is not None
    assert b["payroll_profile"].get("payroll_status") == "missing_data"

    assert b["zus_profile"] is not None
    assert b["zus_profile"].get("registration_status") == "not_submitted"

    assert len(b["onboarding_tasks"]) >= len(DEFAULT_ONBOARDING_TASK_TITLES)
    titles = {t.get("title") for t in b["onboarding_tasks"]}
    assert "Sign employment contract" in titles

    assert isinstance(b["absences"], list)
    assert isinstance(b["leave_requests"], list)


@pytest.mark.asyncio
async def test_handoff_documents_list_reachable_for_question_2(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    """Вопрос 2 (MVP): HR видит тот же контур документов, что и досье кандидата, через workforce row."""
    h = {**recruiter_headers, "Content-Type": "application/json"}
    handoff = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=h,
        json={},
    )
    assert handoff.status_code == 200, handoff.text
    emp_id = handoff.json()["id"]
    assert str(handoff.json().get("candidate_id") or "") == str(candidate_id)

    res = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/documents",
        headers=recruiter_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_handoff_idempotent_same_employee_and_bundle_stable(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    """Повторный handoff по тому же кандидату — тот же сотрудник, HR bundle остаётся валидным."""
    h = {**recruiter_headers, "Content-Type": "application/json"}
    first = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=h,
        json={},
    )
    assert first.status_code == 200, first.text
    emp_id = first.json()["id"]

    second = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=h,
        json={},
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == emp_id

    bundle = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/hr-bundle",
        headers=recruiter_headers,
    )
    assert bundle.status_code == 200, bundle.text
    b = bundle.json()
    assert len(b["employments"]) >= 1
    assert b["payroll_profile"] is not None
    assert b["zus_profile"] is not None
