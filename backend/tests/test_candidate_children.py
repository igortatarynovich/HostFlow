# tests/test_candidate_children.py
import pytest
from httpx import AsyncClient

# ---------------- DOCS ----------------


@pytest.mark.anyio
async def test_documents_crud(
    client: AsyncClient, candidate_id, manager_headers, viewer_headers
):
    # create
    doc_payload = {
        "doc_type": "passport",
        "status": "pending",
        "files": {"front": "file-1.png"},
    }
    r = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=manager_headers,
        json=doc_payload,
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["doc_type"] == "passport"
    assert doc["status"] == "received"
    assert doc["files"] == {"front": "file-1.png"}

    # other type requires custom name and kind
    invalid_payload = {"doc_type": "other"}
    invalid_resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=manager_headers,
        json=invalid_payload,
    )
    assert invalid_resp.status_code == 422

    # list (viewer)
    r = await client.get(
        f"/api/v1/candidates/{candidate_id}/documents", headers=viewer_headers
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(x["id"] == doc["id"] for x in items)

    # patch
    r = await client.patch(
        f"/api/v1/candidates/{candidate_id}/documents/{doc['id']}",
        headers=manager_headers,
        json={"status": "approved"},
    )
    assert r.status_code == 200, r.text
    patched = r.json()
    assert patched["status"] == "approved"

    # delete
    r = await client.delete(
        f"/api/v1/candidates/{candidate_id}/documents/{doc['id']}",
        headers=manager_headers,
    )
    assert r.status_code == 204, r.text


# ---------------- PERMITS ----------------


@pytest.mark.anyio
async def test_permits_crud(
    client: AsyncClient, candidate_id, manager_headers, viewer_headers
):
    # create
    payload = {
        "permit_type": "work_permit",
        "number": "WP-123",
        "status": "requested",
        "issued_on": "2025-08-15",
        "meta": {"source": "HR"},
    }
    r = await client.post(
        f"/api/v1/candidates/{candidate_id}/permits",
        headers=manager_headers,
        json=payload,
    )
    assert r.status_code == 201, r.text
    perm = r.json()
    assert perm["permit_type"] == "work_permit"
    assert perm["status"] == "requested"
    assert perm["issued_on"] == "2025-08-15"

    # list
    r = await client.get(
        f"/api/v1/candidates/{candidate_id}/permits", headers=viewer_headers
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(x["id"] == perm["id"] for x in items)

    # patch
    r = await client.patch(
        f"/api/v1/candidates/{candidate_id}/permits/{perm['id']}",
        headers=manager_headers,
        json={"status": "issued", "expires_on": "2026-08-15"},
    )
    assert r.status_code == 200, r.text
    patched = r.json()
    assert patched["status"] == "issued"
    assert patched["expires_on"] == "2026-08-15"

    # delete
    r = await client.delete(
        f"/api/v1/candidates/{candidate_id}/permits/{perm['id']}",
        headers=manager_headers,
    )
    assert r.status_code == 204, r.text


# ---------------- VISAS ----------------


@pytest.mark.anyio
async def test_visas_crud(
    client: AsyncClient, candidate_id, manager_headers, viewer_headers
):
    # create
    payload = {
        "visa_type": "schengen",
        "number": "V-999",
        "status": "planned",
        "checkpoints": {"appointment": "2025-08-25"},
        "issued_on": "2025-08-10",
    }
    r = await client.post(
        f"/api/v1/candidates/{candidate_id}/visas",
        headers=manager_headers,
        json=payload,
    )
    assert r.status_code == 201, r.text
    visa = r.json()
    assert visa["visa_type"] == "schengen"
    assert visa["status"] == "planned"

    # list
    r = await client.get(
        f"/api/v1/candidates/{candidate_id}/visas", headers=viewer_headers
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(x["id"] == visa["id"] for x in items)

    # patch
    r = await client.patch(
        f"/api/v1/candidates/{candidate_id}/visas/{visa['id']}",
        headers=manager_headers,
        json={
            "status": "submitted",
            "checkpoints": {"appointment": "2025-08-25", "biometrics": "2025-08-27"},
        },
    )
    assert r.status_code == 200, r.text
    patched = r.json()
    assert patched["status"] == "submitted"
    assert set(patched["checkpoints"].keys()) == {"appointment", "biometrics"}

    # delete
    r = await client.delete(
        f"/api/v1/candidates/{candidate_id}/visas/{visa['id']}", headers=manager_headers
    )
    assert r.status_code == 204, r.text


# ---------------- TASKS ----------------


@pytest.mark.anyio
async def test_tasks_crud(
    client: AsyncClient, candidate_id, manager_headers, viewer_headers
):
    # create
    payload = {
        "title": "Позвонить кандидату",
        "due_date": "2025-08-20",
        "priority": "high",
        "assigned_to": "ManagerName",
    }
    r = await client.post(
        f"/api/v1/candidates/{candidate_id}/tasks",
        headers=manager_headers,
        json=payload,
    )
    assert r.status_code == 201, r.text
    task = r.json()
    assert task["title"] == "Позвонить кандидату"
    assert task["priority"] == "high"
    assert task["completed"] is False

    # list
    r = await client.get(
        f"/api/v1/candidates/{candidate_id}/tasks", headers=viewer_headers
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(x["id"] == task["id"] for x in items)

    # patch
    r = await client.patch(
        f"/api/v1/candidates/{candidate_id}/tasks/{task['id']}",
        headers=manager_headers,
        json={"completed": True, "description": "созвон в 15:00"},
    )
    assert r.status_code == 200, r.text
    patched = r.json()
    assert patched["completed"] is True
    assert patched["description"] == "созвон в 15:00"

    # delete
    r = await client.delete(
        f"/api/v1/candidates/{candidate_id}/tasks/{task['id']}", headers=manager_headers
    )
    assert r.status_code == 204, r.text
