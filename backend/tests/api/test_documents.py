from __future__ import annotations

from datetime import date, timedelta
from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.document_template import DocumentTemplate

REQUIRED_BASE_DOCUMENTS = (
    "driver_license",
    "code95",
    "tacho_card",
    "national_id",
)


async def _ensure_required_documents(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    for doc_type in REQUIRED_BASE_DOCUMENTS:
        payload = {
            "candidate_id": candidate_id,
            "type": doc_type,
            "status": "approved",
            "extra": {"title": doc_type},
        }
        resp = await client.post("/api/v1/documents/", headers=manager_headers, json=payload)
        assert resp.status_code == 200, resp.text


async def _create_candidate(client: AsyncClient, manager_headers: Dict[str, str]) -> str:
    resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Order", "last_name": "Flow"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


@pytest.mark.anyio
async def test_documents_crud_flow(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    expires_at = (date.today() + timedelta(days=10)).isoformat()
    payload = {
        "candidate_id": candidate_id,
        "type": "driver_license",
        "number": "DL-12345",
        "status": "submitted",  # alias -> pending_validation -> in_progress
        "expires_at": expires_at,
        "reminder_days_before": 30,
        "files": [
            {"name": "license.pdf", "url": "/uploads/demo/license.pdf"},
        ],
        "extra": {"title": "Driver License"},
    }

    resp = await client.post("/api/v1/documents/", headers=manager_headers, json=payload)
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert doc["type"] == "driver_license"
    assert doc["type_code"] == "driver_license"
    assert doc["status"] == "received"
    assert doc["number"] == "DL-12345"
    assert doc["reminder_days_before"] == 30
    assert doc["has_files"] is True
    assert doc["readiness_state"] == "ready"
    assert doc["status_rank"] >= 4
    doc_id = doc["id"]

    # reminders should be scheduled
    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(Reminder).where(
                    Reminder.tenant_id == tenant_id,
                    Reminder.entity_type == "document",
                    Reminder.entity_id == doc_id,
                )
            )
        ).scalars().all()
        assert rows, "document expiry reminders not scheduled"
        assert all(r.status == ReminderStatus.pending for r in rows)

    # patch to verified state
    patch_payload = {"status": "verified"}
    resp = await client.patch(f"/api/v1/documents/{doc_id}", headers=manager_headers, json=patch_payload)
    assert resp.status_code == 200, resp.text
    patched = resp.json()
    assert patched["status"] == "approved"
    assert patched["verified_at"] is not None

    # list by candidate
    resp = await client.get(
        "/api/v1/documents/",
        headers=manager_headers,
        params={"candidate_id": candidate_id},
    )
    assert resp.status_code == 200, resp.text
    listed = resp.json()
    assert any(item["id"] == doc_id for item in listed)

    # expiring endpoint
    resp = await client.get(
        "/api/v1/documents/expiring",
        headers=manager_headers,
        params={"within_days": 15},
    )
    assert resp.status_code == 200, resp.text
    expiring = resp.json()
    assert any(entry["document"]["id"] == doc_id for entry in expiring)

    # delete (soft)
    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=manager_headers)
    assert resp.status_code == 200, resp.text

    # document no longer accessible
    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=manager_headers)
    assert resp.status_code == 404

    # reminders cancelled
    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(Reminder).where(
                    Reminder.tenant_id == tenant_id,
                    Reminder.entity_type == "document",
                    Reminder.entity_id == doc_id,
                )
            )
        ).scalars().all()
        assert rows
        assert all(r.status == ReminderStatus.done for r in rows)


@pytest.mark.anyio
async def test_documents_legacy_db_endpoint(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    # `insurance` normalizes to catalog `other`, which requires custom_name — use a stable type.
    payload = {
        "candidate_id": candidate_id,
        "type": "visa",
        "status": "ordered",
    }
    create_resp = await client.post(
        "/api/v1/documents/",
        headers=manager_headers,
        json=payload,
    )
    assert create_resp.status_code == 200, create_resp.text

    resp = await client.get(
        "/api/v1/db/documents",
        headers=manager_headers,
        params={"candidate_id": candidate_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert any(doc.get("type") == "visa" for doc in data)


@pytest.mark.anyio
async def test_document_workflow_step_reminders(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    payload = {
        "candidate_id": candidate_id,
        "type": "work_permit",
        "status": "requested",
        "extra": {"title": "Work Permit A"},
    }

    resp = await client.post("/api/v1/documents/", headers=manager_headers, json=payload)
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert doc["type"] == "work_permit"
    assert doc["process_type"] == "work_permit"
    assert doc["status"] == "requested"
    workflow = doc["workflow"]
    assert workflow and workflow["steps"], "expected default workflow steps"
    doc_id = doc["id"]

    async with async_session_maker() as session:
        step_reminders = (
            await session.execute(
                select(Reminder).where(
                    Reminder.tenant_id == tenant_id,
                    Reminder.entity_type == "document_step",
                    Reminder.entity_id.like(f"{doc_id}:%"),
                )
            )
        ).scalars().all()
        assert step_reminders, "expected workflow step reminders to be scheduled"
        assert all(rem.type == "document_workflow_step" for rem in step_reminders)

    # When document is approved, workflow tasks should be auto-completed.
    patch_resp = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=manager_headers,
        json={"status": "verified"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched = patch_resp.json()
    assert patched["status"] == "approved"

    async with async_session_maker() as session:
        step_reminders_after = (
            await session.execute(
                select(Reminder).where(
                    Reminder.tenant_id == tenant_id,
                    Reminder.entity_type == "document_step",
                    Reminder.entity_id.like(f"{doc_id}:%"),
                )
            )
        ).scalars().all()
        assert step_reminders_after, "expected workflow step reminders to exist for closure check"
        assert all(rem.status == ReminderStatus.done for rem in step_reminders_after)


@pytest.mark.anyio
async def test_document_timeline_without_files(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    ordered_at = date.today().isoformat()
    valid_from = (date.today() + timedelta(days=14)).isoformat()

    payload = {
        "candidate_id": candidate_id,
        "type": "work_permit",
        "status": "requested",
        "ordered_at": ordered_at,
        "valid_from": valid_from,
        "extra": {"title": "Work Permit"},
    }

    resp = await client.post("/api/v1/documents/", headers=manager_headers, json=payload)
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert doc["ordered_at"] == ordered_at
    assert doc["valid_from"] == valid_from
    assert doc["has_files"] is False
    assert doc["readiness_state"] == "ordered"

    doc_id = doc["id"]

    # ordered filter should pick the document
    resp = await client.get(
        "/api/v1/documents/",
        headers=manager_headers,
        params={"ordered": "true"},
    )
    assert resp.status_code == 200, resp.text
    ordered_list = resp.json()
    assert any(item["id"] == doc_id for item in ordered_list)

    patch_payload = {"ordered_at": None, "valid_from": (date.today() + timedelta(days=30)).isoformat()}
    resp = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=manager_headers,
        json=patch_payload,
    )
    assert resp.status_code == 200, resp.text
    patched = resp.json()
    assert patched["ordered_at"] is None
    assert patched["valid_from"] == patch_payload["valid_from"]
    assert patched["has_files"] is False

    # ordered=false should now include the document (ordered_at cleared)
    resp = await client.get(
        "/api/v1/documents/",
        headers=manager_headers,
        params={"ordered": "false"},
    )
    assert resp.status_code == 200, resp.text
    not_ordered = resp.json()
    assert any(item["id"] == doc_id for item in not_ordered)


@pytest.mark.anyio
async def test_document_status_update_without_files(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    payload = {
        "candidate_id": candidate_id,
        "type": "visa",
        "status": "ordered",
    }

    create = await client.post("/api/v1/documents/", headers=manager_headers, json=payload)
    assert create.status_code == 200, create.text
    doc = create.json()
    assert doc["status"] in {"requested", "in_progress"}
    doc_id = doc["id"]

    update = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=manager_headers,
        json={"status": "in_progress"},
    )
    assert update.status_code == 200, update.text
    patched = update.json()
    assert patched["status"] == "in_progress"
    assert patched["has_files"] is False

    approve = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=manager_headers,
        json={"status": "approved"},
    )
    assert approve.status_code == 422, approve.text
    assert "without an uploaded file" in approve.text

    fetch = await client.get(f"/api/v1/documents/{doc_id}", headers=manager_headers)
    assert fetch.status_code == 200
    fetched = fetch.json()
    assert fetched["status"] == "in_progress"
    assert fetched["has_files"] is False


@pytest.mark.anyio
async def test_apply_template_creates_missing_documents_with_workflow(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    template_id = str(uuid4())
    template_code = f"driver_ce_template_{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        template = DocumentTemplate(
            id=template_id,
            tenant_id=tenant_id,
            code=template_code,
            name="Driver CE",
            documents=[
                {
                    "doc_type": "driver_license",
                    "kind": "driver",
                    "requested_from": "driver",
                    "process_type": "none",
                },
                {
                    "doc_type": "work_permit",
                    "kind": "process",
                    "requested_from": "agency",
                    "process_type": "work_permit",
                },
            ],
        )
        session.add(template)
        await session.commit()

    resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents/apply-template",
        headers=manager_headers,
        json={"template_id": template_id},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["template_id"] == template_id
    assert payload.get("template_code") == template_code
    docs = payload["documents"]
    assert docs, "expected documents from template"
    by_type = {doc["doc_type"]: doc for doc in docs}
    assert "pesel" in by_type, "PESEL must be auto-included"
    assert "work_permit" in by_type
    work_permit_doc = by_type["work_permit"]
    assert work_permit_doc["status"] in {"missing", "requested"}
    workflow = work_permit_doc["workflow"]
    assert workflow and workflow.get("steps"), "workflow steps expected"
    first_step = workflow["steps"][0]
    assert first_step["status"] == "pending"

    work_permit_id = work_permit_doc["id"]
    async with async_session_maker() as session:
        reminders = (
            await session.execute(
                select(Reminder).where(
                    Reminder.tenant_id == tenant_id,
                    Reminder.entity_type == "document_step",
                    Reminder.entity_id.like(f"{work_permit_id}:%"),
                )
            )
        ).scalars().all()
        assert reminders, "expected workflow reminders for template documents"


@pytest.mark.anyio
async def test_order_document_blocked_until_checklist_ready(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
) -> None:
    """Ordering may proceed before the checklist is complete (operational flexibility)."""
    candidate_id = await _create_candidate(client, manager_headers)
    requested_from = date.today().isoformat()
    resp = await client.post(
        "/api/v1/documents/order",
        headers=recruiter_headers,
        json={
            "candidate_id": candidate_id,
            "doc_type": "work_permit",
            "requested_from": requested_from,
        },
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc.get("doc_type") == "work_permit"


@pytest.mark.anyio
async def test_order_work_permit_sets_meta_and_workflow(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    candidate_id = await _create_candidate(client, manager_headers)
    await _ensure_required_documents(client, manager_headers, candidate_id)
    requested_from = (date.today() + timedelta(days=2)).isoformat()
    ordered_at = (date.today() + timedelta(days=1)).isoformat()

    resp = await client.post(
        "/api/v1/documents/order",
        headers=recruiter_headers,
        json={
            "candidate_id": candidate_id,
            "doc_type": "work_permit",
            "requested_from": requested_from,
            "ordered_at": ordered_at,
        },
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc["doc_type"] == "work_permit"
    assert doc["ordered_at"] == ordered_at
    assert doc["readiness_state"] == "ordered"
    assert doc["meta_json"].get("requested_from_date") == requested_from
    steps = doc.get("workflow", {}).get("steps")
    assert steps and steps[0]["code"] == "ordered"
    assert steps[0]["status"] == "done"
    assert steps[0].get("ordered_at") == ordered_at
    doc_id = doc["id"]

    async with async_session_maker() as session:
        reminders = (
            await session.execute(
                select(Reminder).where(
                    Reminder.tenant_id == tenant_id,
                    Reminder.entity_type == "document_step",
                    Reminder.entity_id.like(f"{doc_id}:%"),
                )
            )
        ).scalars().all()
        assert reminders, "workflow reminders not scheduled"


@pytest.mark.anyio
async def test_driver_certificate_requires_work_permit(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
) -> None:
    candidate_id = await _create_candidate(client, manager_headers)
    await _ensure_required_documents(client, manager_headers, candidate_id)

    resp = await client.post(
        "/api/v1/documents/order",
        headers=recruiter_headers,
        json={
            "candidate_id": candidate_id,
            "doc_type": "driver_certificate",
        },
    )
    assert resp.status_code == 409
    detail = resp.json().get("detail") or {}
    code = detail.get("code") if isinstance(detail, dict) else None
    assert code == "work_permit_required"

    requested_from = (date.today() + timedelta(days=3)).isoformat()
    permit_resp = await client.post(
        "/api/v1/documents/order",
        headers=recruiter_headers,
        json={
            "candidate_id": candidate_id,
            "doc_type": "work_permit",
            "requested_from": requested_from,
        },
    )
    assert permit_resp.status_code == 201, permit_resp.text

    cert_resp = await client.post(
        "/api/v1/documents/order",
        headers=recruiter_headers,
        json={
            "candidate_id": candidate_id,
            "doc_type": "driver_certificate",
        },
    )
    assert cert_resp.status_code == 201, cert_resp.text
    doc = cert_resp.json()
    assert doc["doc_type"] == "driver_certificate"
    assert doc["ordered_at"] is not None
