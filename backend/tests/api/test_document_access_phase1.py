"""ADR-014 Phase 1–2 — resolver read/mutation paths + §11-A acceptance + Phase 2 owner provider."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Dict

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy import text

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.own_company import OwnCompany


@pytest.mark.anyio
async def test_documents_read_scenario_a_own_company_header_mismatch_not_candidate_not_found(
    client: AsyncClient,
    candidate_id: str,
    tenant_id: str,
    manager_headers: Dict[str, str],
) -> None:
    """
    ADR-014 §11-A extended to read endpoints (PR-2): summary, list, checklist, export.json
    do not return Candidate not found solely due to workspace mismatch.
    """
    oc_a = str(uuid.uuid4())
    oc_b = str(uuid.uuid4())

    async with async_session_maker() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, false)"),
                {"tid": tenant_id},
            )
        except Exception:
            pass
        session.add(OwnCompany(id=oc_a, tenant_id=tenant_id, name="pytest own company A"))
        session.add(OwnCompany(id=oc_b, tenant_id=tenant_id, name="pytest own company B"))
        await session.commit()
        await session.execute(
            sa.update(Candidate).where(Candidate.id == candidate_id).values(own_company_id=oc_a)
        )
        await session.commit()

    headers = {**manager_headers, "X-Own-Company-Id": oc_b}
    resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents/summary",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload.get("candidate_id") == candidate_id
    assert "summary" in payload

    list_resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    assert isinstance(list_resp.json(), list)

    checklist_resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/checklist",
        headers=headers,
    )
    assert checklist_resp.status_code == 200, checklist_resp.text
    chk = checklist_resp.json()
    assert chk.get("candidate_id") == candidate_id
    assert "checklist" in chk

    export_resp = await client.get(
        f"/api/v1/db/candidate/{candidate_id}/documents/export.json",
        headers=headers,
    )
    assert export_resp.status_code == 200, export_resp.text
    ex = export_resp.json()
    assert ex.get("candidate_id") == candidate_id
    assert "documents" in ex


@pytest.mark.anyio
async def test_documents_mutation_scenario_a_own_company_header_mismatch_not_candidate_not_found(
    client: AsyncClient,
    candidate_id: str,
    tenant_id: str,
    manager_headers: Dict[str, str],
) -> None:
    """
    ADR-014 §11-A extended to mutations (PR-3): create / patch / presign / mock-upload / delete
    do not return Candidate not found solely due to workspace mismatch.
    """
    oc_a = str(uuid.uuid4())
    oc_b = str(uuid.uuid4())

    async with async_session_maker() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, false)"),
                {"tid": tenant_id},
            )
        except Exception:
            pass
        session.add(OwnCompany(id=oc_a, tenant_id=tenant_id, name="pytest own company A m"))
        session.add(OwnCompany(id=oc_b, tenant_id=tenant_id, name="pytest own company B m"))
        await session.commit()
        await session.execute(
            sa.update(Candidate).where(Candidate.id == candidate_id).values(own_company_id=oc_a)
        )
        await session.commit()

    headers = {**manager_headers, "X-Own-Company-Id": oc_b}
    issued_at = (date.today() - timedelta(days=30)).isoformat()
    expires_at = (date.today() + timedelta(days=90)).isoformat()
    create_payload = {
        "type": "driver_license",
        "candidate_id": candidate_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "number": "DL-PR3-MISMATCH",
        "extra": {"title": "Driver License"},
    }
    create_resp = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=headers,
        json=create_payload,
    )
    if create_resp.status_code == 402:
        detail = create_resp.json().get("detail")
        if isinstance(detail, dict) and detail.get("code") == "document_limit_reached":
            pytest.skip("Test DB tenant at document quota; cannot exercise create in §11-A mutation path")
    assert create_resp.status_code == 201, create_resp.text
    assert "Candidate not found" not in create_resp.text
    created = create_resp.json()
    assert created.get("own_company_id") == oc_a
    doc_id = created["id"]

    patch_resp = await client.patch(
        f"/api/v1/db/documents/{doc_id}",
        headers=headers,
        json={"number": "DL-PR3-PATCHED"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert "Candidate not found" not in patch_resp.text

    presign_resp = await client.post(
        f"/api/v1/db/documents/{doc_id}/presign-upload",
        headers=headers,
    )
    assert presign_resp.status_code == 200, presign_resp.text
    assert "Candidate not found" not in presign_resp.text
    key = presign_resp.json()["fields"]["key"]
    files = {"file": ("license.pdf", b"PDFDATA", "application/pdf")}
    upload_resp = await client.post(
        "/api/v1/db/mock-upload",
        headers=headers,
        data={"key": key},
        files=files,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    assert "Candidate not found" not in upload_resp.text

    del_resp = await client.delete(
        f"/api/v1/db/documents/{doc_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204, del_resp.text
    assert "Candidate not found" not in del_resp.text


def test_destructive_mutation_respects_process_lock_stub() -> None:
    from types import SimpleNamespace

    from fastapi import HTTPException

    from backend.app.modules.documents.document_access_resolver import (
        DocumentAccessContext,
        DocumentAccessResolver,
    )

    ctx = DocumentAccessContext(
        candidate_context=SimpleNamespace(),
        resolved_workspace_own_company_id=None,
        access_policy="destructive_mutate",
        process_locks_stub=frozenset({"destructive_blocked"}),
    )
    with pytest.raises(HTTPException) as exc_info:
        DocumentAccessResolver.ensure_destructive_mutation_allowed(ctx)
    assert exc_info.value.status_code == 403

    ok_ctx = DocumentAccessContext(
        candidate_context=SimpleNamespace(),
        resolved_workspace_own_company_id=None,
    )
    DocumentAccessResolver.ensure_destructive_mutation_allowed(ok_ctx)


def test_document_operation_allowed_blocks_standard_process_locks() -> None:
    from backend.app.modules.documents.document_visibility_and_locks import (
        document_operation_allowed,
    )

    assert document_operation_allowed(access_policy="read", process_locks=frozenset({"employment_handoff_locked"}))
    assert not document_operation_allowed(
        access_policy="destructive_mutate",
        process_locks=frozenset({"employment_handoff_locked"}),
    )
    assert not document_operation_allowed(
        access_policy="destructive_mutate",
        process_locks=frozenset({"payroll_locked"}),
    )
    assert not document_operation_allowed(
        access_policy="destructive_mutate",
        process_locks=frozenset({"transport_compliance_locked"}),
    )


def test_document_access_context_default_access_policy_is_read() -> None:
    from backend.app.modules.documents.document_access_resolver import DocumentAccessContext

    ctx = DocumentAccessContext(
        candidate_context=SimpleNamespace(),
        resolved_workspace_own_company_id="oc",
    )
    assert ctx.access_policy == "read"
    assert ctx.visibility_scope_stub == "recruitment"
    assert ctx.viewer_channel == "recruitment"
    assert "recruitment" in ctx.viewer_readable_scopes
    assert "shared" in ctx.viewer_readable_scopes


@pytest.mark.anyio
async def test_resolve_for_candidate_destructive_document_mutations_enforces_process_lock_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase 2: destructive resolver entrypoint runs process-lock hook before handlers mutate."""
    from fastapi import HTTPException

    from backend.app.modules.documents import document_access_resolver as dar
    from backend.app.modules.documents.document_access_resolver import (
        DocumentAccessContext,
        DocumentAccessResolver,
    )

    fake_cand_ctx = SimpleNamespace(candidate=SimpleNamespace(own_company_id=None))

    async def fake_load(*_a: object, **_k: object) -> object:
        return fake_cand_ctx

    locked = DocumentAccessContext(
        candidate_context=fake_cand_ctx,
        resolved_workspace_own_company_id=None,
        access_policy="destructive_mutate",
        process_locks_stub=frozenset({"destructive_blocked"}),
    )

    monkeypatch.setattr(dar, "load_candidate_documents_owner_context", fake_load)
    monkeypatch.setattr(
        DocumentAccessResolver,
        "_document_access_context_for_policy",
        staticmethod(lambda *_a, **_k: locked),
    )

    with pytest.raises(HTTPException) as exc_info:
        await DocumentAccessResolver.resolve_for_candidate_destructive_document_mutations(
            None,
            "tenant",
            uuid.uuid4(),
            workspace_own_company_header=None,
            viewer_channel="recruitment",
        )
    assert exc_info.value.status_code == 403


def test_destructive_mutation_blocked_for_non_recruitment_viewer() -> None:
    from fastapi import HTTPException

    from backend.app.modules.documents.document_access_resolver import (
        DocumentAccessContext,
        DocumentAccessResolver,
    )

    ctx = DocumentAccessContext(
        candidate_context=SimpleNamespace(),
        resolved_workspace_own_company_id=None,
        access_policy="destructive_mutate",
        process_locks_stub=frozenset(),
        viewer_channel="hr",
    )
    with pytest.raises(HTTPException) as exc_info:
        DocumentAccessResolver.ensure_destructive_mutation_allowed(ctx)
    assert exc_info.value.status_code == 403
