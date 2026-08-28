from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.document_ruleset import DocumentRulesetVersion


@pytest.mark.anyio
async def test_documents_db_flow(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    # Create document via new DB module
    issued_at = (date.today() - timedelta(days=30)).isoformat()
    expires_at = (date.today() + timedelta(days=90)).isoformat()
    payload = {
        "type": "driver_license",
        "candidate_id": candidate_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "number": "DL-XYZ-001",
        "extra": {"title": "Driver License"},
        "files": [
            {"name": "license.pdf", "url": "/uploads/demo/license.pdf"},
        ],
    }
    create_resp = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=manager_headers,
        json=payload,
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["type"] == "driver_license"
    assert created["version"] == 1
    doc_id = created["id"]

    # Validate meta schema (should fail because required fields missing)
    meta_resp = await client.post(
        "/api/v1/db/document-types/prawo_jazdy/validate-meta",
        headers=manager_headers,
        json={"issued_at": issued_at},
    )
    assert meta_resp.status_code == 200
    meta_data = meta_resp.json()
    assert meta_data["valid"] is False
    assert any(err["field"] == "number" for err in meta_data["errors"])

    # Approve document and ensure check recorded
    check_payload = {
        "decision": "approved",
        "comment": "Looks good",
    }
    check_resp = await client.post(
        f"/api/v1/db/documents/{doc_id}/check",
        headers=manager_headers,
        json=check_payload,
    )
    assert check_resp.status_code == 200, check_resp.text
    checked = check_resp.json()
    assert checked["status"] in {"verified", "approved"}
    assert checked["last_check"]["decision"] == "approved"
    assert checked["version"] == 2

    # Fetch single document with checks included
    get_resp = await client.get(
        f"/api/v1/db/documents/{doc_id}",
        params={"include_checks": True},
        headers=manager_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    got = get_resp.json()
    assert got["checks"], "Expected checks array to be returned"
    assert got["checks"][0]["decision"] == "approved"

    # List documents and ensure last_check present
    list_resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=manager_headers,
    )
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert listed and listed[0]["last_check"]["decision"] == "approved"

    # Presign + upload mock file
    presign_resp = await client.post(
        f"/api/v1/db/documents/{doc_id}/presign-upload",
        headers=manager_headers,
    )
    assert presign_resp.status_code == 200
    presign = presign_resp.json()
    key = presign["fields"]["key"]
    files = {"file": ("license.pdf", b"PDFDATA", "application/pdf")}
    data = {"key": key}
    upload_resp = await client.post(
        "/api/v1/db/mock-upload",
        headers=manager_headers,
        data=data,
        files=files,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    upload_data = upload_resp.json()
    assert upload_data["ok"] is True

    # Document should now contain file and incremented version
    after_upload = (
        await client.get(f"/api/v1/db/documents/{doc_id}", headers=manager_headers)
    ).json()
    assert after_upload["version"] >= 3
    assert after_upload["files"], "Expected files after upload"
    assert after_upload["has_files"] is True
    assert after_upload["readiness_state"] == "ready"

    # Extract metadata (OCR mock)
    extract_resp = await client.post(
        f"/api/v1/db/documents/{doc_id}/extract",
        headers=manager_headers,
    )
    assert extract_resp.status_code == 200
    extract = extract_resp.json()
    assert "fields" in extract

    # Create an ordered document without files to ensure readiness reflects the order date
    ordered_payload = {
        "candidate_id": candidate_id,
        "doc_type": "visa",
        "ordered_at": date.today().isoformat(),
        "status": "requested",
    }
    ordered_doc_resp = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=manager_headers,
        json=ordered_payload,
    )
    assert ordered_doc_resp.status_code == 201, ordered_doc_resp.text
    ordered_doc = ordered_doc_resp.json()
    assert ordered_doc["readiness_state"] == "ordered"

    # Force legacy string payload for the active ruleset to ensure normalization works.
    async with async_session_maker() as session:
        version_row = await session.execute(select(DocumentRulesetVersion).limit(1))
        ruleset_version = version_row.scalar_one()
        ruleset_version_id = ruleset_version.id
        original_payload = ruleset_version.json_data
        ruleset_version.json_data = json.dumps(original_payload or {})
        await session.commit()

    try:
        # Summary endpoint should respond with documents and summary payload
        summary_resp = await client.get(
            f"/api/v1/db/candidate/{candidate_id}/documents/summary",
            headers=manager_headers,
        )
        assert summary_resp.status_code == 200
        summary_data = summary_resp.json()
        assert summary_data["documents"]
        assert summary_data["summary"]["required"]["total"] >= 0
    finally:
        # Restore ruleset payload to avoid side effects for other tests.
        async with async_session_maker() as session:
            version_row = await session.execute(
                select(DocumentRulesetVersion).where(
                    DocumentRulesetVersion.id == ruleset_version_id
                )
            )
            persisted = version_row.scalar_one_or_none()
            if persisted:
                persisted.json_data = original_payload
                await session.commit()


    # Checklist endpoint
    checklist_resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/checklist",
        headers=manager_headers,
    )
    assert checklist_resp.status_code == 200
    checklist = checklist_resp.json()
    assert "checklist" in checklist

    # Export JSON & CSV
    export_json = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents/export.json",
        headers=manager_headers,
    )
    assert export_json.status_code == 200
    assert export_json.json()["documents"]

    export_csv = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents/export.csv",
        headers=manager_headers,
    )
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers["Content-Type"]

    # Ruleset retrieval and update
    ruleset_resp = await client.get("/api/v1/db/ruleset", headers=manager_headers)
    assert ruleset_resp.status_code == 200
    ruleset = ruleset_resp.json()
    assert ruleset["ruleset"]
    assert ruleset["signature"]

    patch_payload = {
        "ruleset": {"requiredTypes": ["national_id"], "optionalTypes": []},
        "comment": "pytest revision",
    }
    patch_resp = await client.patch(
        "/api/v1/db/ruleset",
        headers=manager_headers,
        json=patch_payload,
    )
    assert patch_resp.status_code == 200
    new_ruleset = patch_resp.json()
    assert new_ruleset["version"] >= ruleset["version"]
    assert new_ruleset["ruleset"]["requiredTypes"] == ["national_id"]
    assert new_ruleset["is_active"] is True
    assert new_ruleset["signature"] and new_ruleset["signature"] != ruleset["signature"]
    assert new_ruleset["origin_version_id"] is None
    assert new_ruleset["rollback_comment"] is None

    # List versions should contain at least the latest
    versions_resp = await client.get(
        "/api/v1/db/ruleset/versions", headers=manager_headers
    )
    assert versions_resp.status_code == 200
    versions = versions_resp.json()
    assert versions and versions[0]["version"] == new_ruleset["version"]
    assert all("signature" in item for item in versions)

    # Create draft ruleset version without activation
    draft_payload = {
        "ruleset": {
            "requiredTypes": ["national_id"],
            "optionalTypes": ["code95"],
        },
        "comment": "draft ruleset for tests",
        "activate": False,
    }
    draft_resp = await client.post(
        "/api/v1/db/ruleset/versions",
        headers=manager_headers,
        json=draft_payload,
    )
    assert draft_resp.status_code == 200
    draft_version = draft_resp.json()
    assert draft_version["is_active"] is False
    assert draft_version["version"] == new_ruleset["version"] + 1

    # Fetch single version
    get_version_resp = await client.get(
        f"/api/v1/db/ruleset/versions/{draft_version['id']}",
        headers=manager_headers,
    )
    assert get_version_resp.status_code == 200
    fetched_version = get_version_resp.json()
    assert fetched_version["id"] == draft_version["id"]
    assert fetched_version["ruleset"]["optionalTypes"] == ["code95"]

    # Diff between versions should reflect optionalTypes addition
    diff_resp = await client.get(
        f"/api/v1/db/ruleset/versions/{draft_version['id']}/diff",
        headers=manager_headers,
    )
    assert diff_resp.status_code == 200
    diff = diff_resp.json()
    assert diff["version_id"] == draft_version["id"]
    assert diff["diff"]["summary"]["changed"] >= 1

    # Activate the draft version
    activate_resp = await client.post(
        f"/api/v1/db/ruleset/versions/{draft_version['id']}/activate",
        headers=manager_headers,
    )
    assert activate_resp.status_code == 200
    activated = activate_resp.json()
    assert activated["is_active"] is True
    assert activated["id"] == draft_version["id"]

    # Roll back to previous version
    rollback_resp = await client.post(
        f"/api/v1/db/ruleset/versions/{new_ruleset['id']}/rollback",
        headers=manager_headers,
        json={"comment": "restore previous ruleset"},
    )
    assert rollback_resp.status_code == 200
    rollback_version = rollback_resp.json()
    assert rollback_version["is_active"] is True
    assert rollback_version["origin_version_id"] == new_ruleset["id"]
    assert rollback_version["rollback_comment"] == "restore previous ruleset"

    # Checklist request should log usage entry
    checklist_resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/checklist",
        headers=manager_headers,
    )
    assert checklist_resp.status_code == 200
    usage_resp = await client.get(
        "/api/v1/db/ruleset/usage",
        headers=manager_headers,
    )
    assert usage_resp.status_code == 200
    usage = usage_resp.json()
    assert usage["items"]
    assert any(item["used_in"] == "checklist" for item in usage["items"])


@pytest.mark.anyio
async def test_cannot_approve_document_without_file(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    create_resp = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=manager_headers,
        json={"type": "passport", "extra": {"title": "Passport"}},
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["has_files"] is False
    doc_id = created["id"]

    check_resp = await client.post(
        f"/api/v1/db/documents/{doc_id}/check",
        headers=manager_headers,
        json={"decision": "approved", "comment": "no file"},
    )
    assert check_resp.status_code == 422, check_resp.text
    assert "without an uploaded file" in check_resp.text

    fetched = (
        await client.get(f"/api/v1/db/documents/{doc_id}", headers=manager_headers)
    ).json()
    assert fetched["has_files"] is False
    assert fetched["status"] not in {"approved", "verified", "received"}
    assert (fetched.get("document_runtime") or {}).get("workflow_status") == "missing"
