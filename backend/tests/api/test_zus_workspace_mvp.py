"""ZUS workspace MVP: list/create/patch workforce_zus_workspace_tasks."""

from __future__ import annotations

from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_zus_workspace_list_create_patch(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "ZUS workspace queue subject",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    unique_kind = f"zus_registration_review_{uuid4().hex[:12]}"

    before = await client.get(
        "/api/v1/workforce/zus-workspace/tasks",
        headers=hr_officer_headers,
        params={"task_kind": unique_kind},
    )
    assert before.status_code == 200, before.text
    assert before.json().get("total") == 0

    post = await client.post(
        "/api/v1/workforce/zus-workspace/tasks",
        headers=h,
        json={
            "employee_id": emp_id,
            "workspace_lane": "task_queue",
            "task_kind": unique_kind,
            "title": "Zgłoszenie do ZUS",
            "status": "open",
        },
    )
    assert post.status_code == 201, post.text
    tid = post.json()["id"]
    assert post.json()["employee_id"] == emp_id

    listed = await client.get(
        "/api/v1/workforce/zus-workspace/tasks",
        headers=hr_officer_headers,
        params={"workspace_lane": "task_queue", "task_kind": unique_kind},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1

    patch = await client.patch(
        f"/api/v1/workforce/zus-workspace/tasks/{tid}",
        headers=h,
        json={"status": "in_progress", "form_kind": "ZUA", "form_status": "draft"},
    )
    assert patch.status_code == 200, patch.text
    body = patch.json()
    assert body["status"] == "in_progress"
    assert body.get("form_kind") == "ZUA"

    by_form = await client.get(
        "/api/v1/workforce/zus-workspace/tasks",
        headers=hr_officer_headers,
        params={"form_kind": "ZUA", "task_kind": unique_kind},
    )
    assert by_form.status_code == 200, by_form.text
    assert by_form.json()["total"] == 1


@pytest.mark.asyncio
async def test_recruiter_zus_workspace_forbidden(client: AsyncClient, recruiter_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/workforce/zus-workspace/tasks", headers=recruiter_headers)
    assert resp.status_code == 403, resp.text
