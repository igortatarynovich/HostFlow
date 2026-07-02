"""A3-B1 — Requirements workspace bundle API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import (
    DRIVER_CE_REQUIREMENTS,
    approve_evidence_api,
    get_requirements_workspace,
    link_evidence_document,
    post_document,
    select_evidence,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def test_workspace_returns_bundle_shape(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    workspace = await get_requirements_workspace(client, manager_headers, str(candidate.id))

    assert workspace["schema_version"] == "requirements_workspace_v1"
    assert workspace["candidate_id"] == str(candidate.id)
    assert workspace["entity_profile_code"] == "recruitment.candidate.driver_ce"
    assert workspace["vacancy_id"] == str(candidate.vacancy_id)
    assert workspace["can_edit"] is True
    assert "evaluated_at" in workspace

    checklist = workspace["checklist"]
    codes = {item["requirement_code"] for item in checklist["requirements"]}
    assert codes == set(DRIVER_CE_REQUIREMENTS)

    summary = workspace["summary"]
    assert summary["total_requirements"] >= len(DRIVER_CE_REQUIREMENTS)
    assert summary["fulfilled_count"] >= 0
    assert summary["all_fulfilled"] is False
    assert summary["handoff_ready"] is False
    assert summary["blocking_open_count"] > 0

    field_requirements = workspace["field_requirements"]
    assert isinstance(field_requirements["required_fields"], list)
    assert field_requirements["missing_count"] >= 0

    transfer = workspace["transfer_readiness"]
    assert transfer["policy_version"] == "transfer_policy_v1"
    assert transfer["transfer_allowed"] is False
    assert isinstance(transfer["blocking_reasons"], list)

    assert workspace["pipeline_blockers"]["source"] == "requirement_fulfillment_v1"
    assert workspace["operational_requirements"] == []


async def test_workspace_handoff_ready_after_all_evidence_approved(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    patch_resp = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={
            "extra": {
                "citizenship": "UA",
                "experience_eu_years": "5",
                "address": "Warsaw, Test Street 1",
            },
            "personal_data": {
                "address": "Warsaw, Test Street 1",
                "citizenship": "UA",
            },
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text

    flows = [
        ("identity_document", "identity_any", "passport"),
        ("legal_stay_confirmation", "legal_stay_any", "karta_pobytu"),
        ("driver_license_with_code95", "combined_eu_license", "driver_license_code95"),
        ("tachograph_card", "tacho_any", "tacho_card"),
        ("medical_fitness", "medical_any", "medical_certificate"),
        ("psychological_tests", "psychological_any", "psychotest"),
        ("voivodeship_decision", "decision_any", "decision"),
    ]
    for requirement_code, variant_code, doc_type in flows:
        doc_id = await post_document(client, manager_headers, candidate_id=cid, doc_type=doc_type)
        evidence = await select_evidence(
            client,
            manager_headers,
            candidate_id=cid,
            requirement_code=requirement_code,
            evidence_variant_code=variant_code,
        )
        await link_evidence_document(
            client,
            manager_headers,
            candidate_id=cid,
            evidence_id=evidence["evidence_id"],
            document_id=doc_id,
        )
        await approve_evidence_api(
            client,
            manager_headers,
            candidate_id=cid,
            evidence_id=evidence["evidence_id"],
        )

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    assert workspace["checklist"]["all_fulfilled"] is True
    assert workspace["summary"]["all_fulfilled"] is True
    requirement_gate = workspace["transfer_readiness"].get("requirement_gate") or {}
    assert requirement_gate.get("satisfied") is True
    requirement_engine = workspace["transfer_readiness"].get("requirement_engine") or {}
    if requirement_engine:
        assert requirement_engine.get("satisfied") is True


async def test_workspace_includes_field_requirements_missing_address(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    workspace = await get_requirements_workspace(client, manager_headers, str(candidate.id))

    field_codes = {row["qualified_code"] for row in workspace["field_requirements"]["required_fields"]}
    assert "platform.identity.address" in field_codes
    address_row = next(
        row
        for row in workspace["field_requirements"]["required_fields"]
        if row["qualified_code"] == "platform.identity.address"
    )
    assert address_row["satisfied"] is False
