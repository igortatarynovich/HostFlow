"""A3-B2 — transfer-readiness target_stage query."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import (
    approve_evidence_api,
    get_requirements_workspace,
    link_evidence_document,
    post_document,
    select_evidence,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio

_DRIVER_CE_FLOWS = [
    ("identity_document", "identity_any", "passport"),
    ("legal_stay_confirmation", "legal_stay_any", "karta_pobytu"),
    ("driver_license_with_code95", "combined_eu_license", "driver_license_code95"),
    ("tachograph_card", "tacho_any", "tacho_card"),
    ("medical_fitness", "medical_any", "medical_certificate"),
    ("psychological_tests", "psychological_any", "psychotest"),
    ("voivodeship_decision", "decision_any", "decision"),
]


async def _close_driver_ce_requirements(
    client: AsyncClient,
    headers: dict[str, str],
    candidate_id: str,
) -> None:
    patch_resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=headers,
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

    for requirement_code, variant_code, doc_type in _DRIVER_CE_FLOWS:
        doc_id = await post_document(client, headers, candidate_id=candidate_id, doc_type=doc_type)
        evidence = await select_evidence(
            client,
            headers,
            candidate_id=candidate_id,
            requirement_code=requirement_code,
            evidence_variant_code=variant_code,
        )
        await link_evidence_document(
            client,
            headers,
            candidate_id=candidate_id,
            evidence_id=evidence["evidence_id"],
            document_id=doc_id,
        )
        await approve_evidence_api(
            client,
            headers,
            candidate_id=candidate_id,
            evidence_id=evidence["evidence_id"],
        )


async def test_transfer_readiness_without_target_stage_omits_requirement_gate(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    resp = await client.get(
        f"/api/v1/candidates/{cid}/transfer-readiness",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("requirement_gate") is None


async def test_transfer_readiness_target_stage_includes_requirement_gate(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    before = await client.get(
        f"/api/v1/candidates/{cid}/transfer-readiness",
        headers=manager_headers,
        params={"target_stage": "ready_for_handoff"},
    )
    assert before.status_code == 200, before.text
    gate_before = before.json().get("requirement_gate") or {}
    assert gate_before.get("applied") is True
    assert gate_before.get("satisfied") is False

    await _close_driver_ce_requirements(client, manager_headers, cid)

    after = await client.get(
        f"/api/v1/candidates/{cid}/transfer-readiness",
        headers=manager_headers,
        params={"target_stage": "ready_for_handoff"},
    )
    assert after.status_code == 200, after.text
    body = after.json()
    gate_after = body.get("requirement_gate") or {}
    assert gate_after.get("applied") is True
    assert gate_after.get("satisfied") is True

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    workspace_gate = workspace["transfer_readiness"].get("requirement_gate") or {}
    assert workspace_gate.get("satisfied") is True
    assert workspace["checklist"]["all_fulfilled"] is True
