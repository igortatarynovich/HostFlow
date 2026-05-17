"""ADR-014 Phase 2 — HR workforce document open integration tests."""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, timedelta
from typing import Dict

import pytest
from httpx import AsyncClient


async def _post_db_doc(
    client: AsyncClient,
    headers: dict[str, str],
    candidate_id: str,
    doc_type: str,
    number: str,
) -> dict:
    issued = (date.today() - timedelta(days=200)).isoformat()
    expires = (date.today() + timedelta(days=500)).isoformat()
    r = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=headers,
        json={
            "type": doc_type,
            "number": number,
            "issued_at": issued,
            "expires_at": expires,
            "status": "received",
        },
    )
    if r.status_code == 402:
        pytest.skip("document quota")
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.anyio
async def test_hr_workforce_list_emits_workforce_open_urls_not_candidate_file(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tag = uuid.uuid4().hex[:8]
    tacho = await _post_db_doc(
        client, manager_headers, candidate_id, "tacho_card", f"TACHO-{tag}"
    )
    permit = await _post_db_doc(
        client, manager_headers, candidate_id, "residence_permit", f"RP-{tag}"
    )

    create = await client.post(
        "/api/v1/workforce/employees",
        headers=hr_officer_headers,
        json={
            "display_name": f"Open resolver {tag}",
            "company_id": bootstrap["company_id"],
            "candidate_id": candidate_id,
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    res = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/documents",
        headers=hr_officer_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    by_id = {row["id"]: row for row in body}
    assert tacho["id"] in by_id
    assert permit["id"] in by_id

    dump = json.dumps(body)
    assert not re.search(
        r"/api/v1/candidates/[^/\"]+/documents/[^/\"]+/file",
        dump,
    ), dump

    for doc_id in (tacho["id"], permit["id"]):
        row = by_id[doc_id]
        url = row.get("open_url") or row.get("file_url")
        assert url == f"/api/v1/workforce/employees/{emp_id}/documents/{doc_id}/file"
        assert row.get("document_open_context") == "hr_workforce_employee"


@pytest.mark.anyio
async def test_db_hr_channel_not_used_for_employee_transport_doc_workforce_file_ok(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tag = uuid.uuid4().hex[:8]
    tacho = await _post_db_doc(
        client, manager_headers, candidate_id, "tacho_card", f"TACHO2-{tag}"
    )
    doc_id = tacho["id"]

    create = await client.post(
        "/api/v1/workforce/employees",
        headers=hr_officer_headers,
        json={
            "display_name": f"File route {tag}",
            "company_id": bootstrap["company_id"],
            "candidate_id": candidate_id,
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    db_hr = await client.get(
        f"/api/v1/db/documents/{doc_id}/file",
        headers={**hr_officer_headers, "X-Document-Viewer-Channel": "hr"},
    )
    assert db_hr.status_code == 404, db_hr.text

    wf = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/documents/{doc_id}/file",
        headers=hr_officer_headers,
    )
    assert wf.status_code != 401, wf.text
    assert wf.status_code != 500, wf.text
    assert wf.status_code in (200, 403, 404), wf.text


@pytest.mark.anyio
async def test_recruitment_open_context_denies_hr_only_medical(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
) -> None:
    from backend.app.modules.documents.document_open_resolver import (
        DocumentOpenContext,
        resolve_document_open,
    )

    tag = uuid.uuid4().hex[:8]
    med = await _post_db_doc(
        client, manager_headers, candidate_id, "medical_certificate", f"MED-{tag}"
    )

    decision = resolve_document_open(
        DocumentOpenContext(
            surface="recruitment_candidate",
            tenant_id="test",
            document_id=med["id"],
            candidate_id=candidate_id,
            doc_type="medical_certificate",
        )
    )
    assert decision.allowed is False
    assert decision.deny_reason == "document_type_not_visible_in_surface"
