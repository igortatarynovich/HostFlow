"""Viewer-aware document read visibility (ADR-014, no policy graph)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict

import pytest
from httpx import AsyncClient

from backend.app.modules.documents.document_visibility_and_locks import (
    document_type_primary_visibility_scope,
    document_visible_to_viewer,
    viewer_readable_scopes,
)


def test_viewer_readable_scopes_include_shared() -> None:
    assert viewer_readable_scopes("hr") == frozenset({"hr", "shared"})
    assert viewer_readable_scopes("transport") == frozenset({"transport", "shared"})
    assert viewer_readable_scopes("finance") == frozenset({"finance", "shared"})


def test_primary_scope_mapping() -> None:
    assert document_type_primary_visibility_scope("passport") == "recruitment"
    assert document_type_primary_visibility_scope("driver_license") == "shared"
    assert document_type_primary_visibility_scope("medical_certificate") == "hr"
    assert document_type_primary_visibility_scope("shared_notice") == "shared"


def test_document_visible_to_viewer_matrix() -> None:
    assert document_visible_to_viewer("passport", "recruitment")
    assert not document_visible_to_viewer("passport", "transport")
    assert document_visible_to_viewer("driver_license", "transport")
    assert document_visible_to_viewer("driver_license", "hr")
    assert document_visible_to_viewer("medical_certificate", "hr")
    assert not document_visible_to_viewer("medical_certificate", "transport")
    assert document_visible_to_viewer("shared_notice", "finance")


@pytest.mark.anyio
async def test_invalid_x_document_viewer_channel_422(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers={**manager_headers, "X-Document-Viewer-Channel": "unknown"},
        params={"fill_missing": "false"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.anyio
async def test_summary_includes_document_access_trace_when_debug_env(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOSTFLOW_DOCUMENT_ACCESS_DEBUG", "1")
    resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents/summary",
        headers={**manager_headers, "X-Document-Viewer-Channel": "transport"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    trace = body.get("document_access_trace")
    assert isinstance(trace, dict), body.keys()
    assert trace.get("viewer_channel") == "transport"
    assert trace.get("surface") == "candidate_documents_summary"
    assert "physical_documents_total" in trace
    assert "viewer_readable_scopes" in trace


@pytest.mark.anyio
async def test_transport_viewer_hides_recruitment_scoped_passport(
    client: AsyncClient,
    candidate_id: str,
    manager_headers: Dict[str, str],
) -> None:
    issued_at = (date.today() - timedelta(days=300)).isoformat()
    expires_at = (date.today() + timedelta(days=600)).isoformat()
    create_payload = {
        "type": "passport",
        "candidate_id": candidate_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "number": "PP-PYTEST-VIS",
        "extra": {"country": "PL", "nationality": "PL"},
    }
    create_resp = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=manager_headers,
        json=create_payload,
    )
    if create_resp.status_code == 402:
        detail = create_resp.json().get("detail")
        if isinstance(detail, dict) and detail.get("code") == "document_limit_reached":
            pytest.skip("Test tenant at document quota")
    assert create_resp.status_code == 201, create_resp.text
    doc_id = create_resp.json()["id"]

    transport_headers = {**manager_headers, "X-Document-Viewer-Channel": "transport"}
    list_tr = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=transport_headers,
        params={"fill_missing": "false"},
    )
    assert list_tr.status_code == 200, list_tr.text
    ids_tr = {d["id"] for d in list_tr.json()}
    assert doc_id not in ids_tr

    get_tr = await client.get(
        f"/api/v1/db/documents/{doc_id}",
        headers=transport_headers,
    )
    assert get_tr.status_code == 404, get_tr.text

    list_def = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=manager_headers,
        params={"fill_missing": "false"},
    )
    assert list_def.status_code == 200
    ids_def = {d["id"] for d in list_def.json()}
    assert doc_id in ids_def
