"""A3-C — Workspace combined vs separate driver license paths."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import (
    approve_evidence_api,
    checklist_item,
    get_requirements_workspace,
    link_evidence_document,
    post_document,
    select_evidence,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio

_LICENSE_META = {
    "extracted_fields": {
        "number": "DL-123456",
        "categories": ["CE"],
        "issued_at": "2020-01-01",
        "expires_at": "2030-01-01",
        "country": "PL",
    }
}

_CODE95_META = {
    "extracted_fields": {
        "number": "C95-998877",
        "issued_at": "2021-06-01",
        "expires_at": "2026-06-01",
        "country": "PL",
    }
}


async def test_workspace_combined_license_path_satisfied(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    doc_id = await post_document(
        client,
        manager_headers,
        candidate_id=cid,
        doc_type="driver_license_code95",
        meta=_LICENSE_META,
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=cid,
        requirement_code="driver_license_with_code95",
        evidence_variant_code="combined_eu_license",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=cid,
        evidence_id=evidence["evidence_id"],
        document_id=doc_id,
    )

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    item = checklist_item(workspace["checklist"], "driver_license_with_code95")
    alts = item["evaluation"]["alternatives_evaluated"]
    assert len(alts) == 2
    combined = next(row for row in alts if row["alternative_code"] == "combined_eu_license")
    separate = next(row for row in alts if row["alternative_code"] == "separate_documents")
    assert combined["status"] == "satisfied"
    assert separate["status"] == "missing"

    docs = item["candidate_evidence"]["documents"]
    assert docs[0]["extracted_fields"]["number"] == "DL-123456"
    assert docs[0]["required_extraction_fields"]
    assert docs[0]["missing_extraction_fields"] == []


async def test_workspace_separate_license_path_satisfied(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    license_id = await post_document(
        client,
        manager_headers,
        candidate_id=cid,
        doc_type="driver_license",
        meta=_LICENSE_META,
    )
    code95_id = await post_document(
        client,
        manager_headers,
        candidate_id=cid,
        doc_type="code95",
        meta=_CODE95_META,
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=cid,
        requirement_code="driver_license_with_code95",
        evidence_variant_code="separate_documents",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=cid,
        evidence_id=evidence["evidence_id"],
        document_id=license_id,
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=cid,
        evidence_id=evidence["evidence_id"],
        document_id=code95_id,
    )

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    item = checklist_item(workspace["checklist"], "driver_license_with_code95")
    alts = item["evaluation"]["alternatives_evaluated"]
    separate = next(row for row in alts if row["alternative_code"] == "separate_documents")
    assert separate["status"] == "satisfied"
    assert len(separate["document_type_codes"]) == 2


async def test_workspace_separate_path_partial_when_only_license_linked(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    license_id = await post_document(
        client,
        manager_headers,
        candidate_id=cid,
        doc_type="driver_license",
        meta=_LICENSE_META,
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=cid,
        requirement_code="driver_license_with_code95",
        evidence_variant_code="separate_documents",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=cid,
        evidence_id=evidence["evidence_id"],
        document_id=license_id,
    )

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    item = checklist_item(workspace["checklist"], "driver_license_with_code95")
    assert item["evaluation"]["status"] == "pending_verification"
    alts = item["evaluation"]["alternatives_evaluated"]
    separate = next(row for row in alts if row["alternative_code"] == "separate_documents")
    assert separate["status"] == "pending_verification"
    assert separate.get("partial") is True


async def test_workspace_approve_blocked_when_extraction_fields_missing(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    doc_id = await post_document(
        client,
        manager_headers,
        candidate_id=cid,
        doc_type="passport",
        meta={"extracted_fields": {"country": "UA"}},
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=cid,
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=cid,
        evidence_id=evidence["evidence_id"],
        document_id=doc_id,
    )

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    item = checklist_item(workspace["checklist"], "identity_document")
    assert item["evaluation"]["extraction_incomplete"] is True
    assert any(
        row.get("code") == "document_extraction_field_missing"
        for row in item["evaluation"].get("blockers") or []
    )

    approve_resp = await client.post(
        f"/api/v1/candidates/{cid}/requirements/evidence/{evidence['evidence_id']}/approve",
        headers=manager_headers,
    )
    assert approve_resp.status_code == 400
    assert "Missing extraction fields" in approve_resp.text
