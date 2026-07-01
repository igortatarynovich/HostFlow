"""Integration: pipeline forward guard uses requirement fulfillment blockers."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import (
    approve_evidence_api,
    get_checklist,
    link_evidence_document,
    post_document,
    select_evidence,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _noop_rodo_enforcement_for_requirement_pipeline_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "backend.app.api.v1.candidates.service._enforce_rodo_before_contact_stage",
        _noop,
    )


async def _move_to_docs_wait(
    client: AsyncClient,
    headers: dict[str, str],
    candidate_id: str,
) -> None:
    for stage in ("contacted", "questionnaire_submitted", "docs_wait"):
        resp = await client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={"stage": stage},
        )
        assert resp.status_code == 200, resp.text


async def _fulfill_requirement(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    requirement_code: str,
    variant_code: str,
    doc_type: str,
) -> None:
    doc_id = await post_document(
        client,
        headers,
        candidate_id=candidate_id,
        doc_type=doc_type,
    )
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


async def test_pipeline_guard_blocks_with_requirement_codes_not_doc_types(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    await _move_to_docs_wait(client, manager_headers, str(candidate.id))

    blocked = await client.patch(
        f"/api/v1/candidates/{candidate.id}",
        headers=manager_headers,
        json={"stage": "docs_got"},
    )
    assert blocked.status_code == 409, blocked.text
    detail = blocked.json()["detail"]
    assert detail["code"] == "stage_blocked_by_requirements"
    missing = detail.get("missing_requirements") or detail.get("missing_types") or []
    assert "identity_document" in missing
    assert "passport" not in missing
    assert "visa" not in missing


async def test_pipeline_guard_allows_forward_when_requirements_fulfilled(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    await _move_to_docs_wait(client, manager_headers, str(candidate.id))

    await _fulfill_requirement(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        variant_code="identity_any",
        doc_type="passport",
    )
    await _fulfill_requirement(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="driver_license_with_code95",
        variant_code="combined_eu_license",
        doc_type="driver_license_code95",
    )
    await _fulfill_requirement(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="tachograph_card",
        variant_code="tacho_any",
        doc_type="tachograph_card",
    )

    checklist = await get_checklist(client, manager_headers, str(candidate.id))
    assert checklist["all_fulfilled"] is True
    pb = checklist["pipeline_blockers"]
    assert pb["all_fulfilled"] is True
    assert pb["missing_requirements"] == []

    forward = await client.patch(
        f"/api/v1/candidates/{candidate.id}",
        headers=manager_headers,
        json={"stage": "docs_got"},
    )
    assert forward.status_code == 200, forward.text


async def test_checklist_pipeline_blockers_single_legal_stay_row(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Visa/karta variants collapse to one Legal Stay blocker in checklist pipeline_blockers."""
    from backend.app.services import candidate_evidence_service as svc

    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)

    async def _codes_with_legal_stay(db, *, tenant_id: str, candidate):  # type: ignore[no-untyped-def]
        return [
            "identity_document",
            "driver_license_with_code95",
            "tachograph_card",
            "legal_stay_confirmation",
        ]

    monkeypatch.setattr(svc, "resolve_required_requirement_codes", _codes_with_legal_stay)

    checklist = await get_checklist(client, manager_headers, str(candidate.id))
    pb = checklist["pipeline_blockers"]
    assert pb["missing_requirements"].count("legal_stay_confirmation") == 1
    assert "visa" not in pb["missing_requirements"]
    assert "karta_pobytu" not in pb["missing_requirements"]

    visa_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="visa",
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="legal_stay_confirmation",
        evidence_variant_code="legal_stay_any",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=evidence["evidence_id"],
        document_id=visa_id,
    )
    await approve_evidence_api(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=evidence["evidence_id"],
    )

    checklist_after = await get_checklist(client, manager_headers, str(candidate.id))
    legal_item = next(
        row
        for row in checklist_after["requirements"]
        if row["requirement_code"] == "legal_stay_confirmation"
    )
    assert legal_item["fulfilled"] is True
    assert "legal_stay_confirmation" not in checklist_after["pipeline_blockers"]["missing_requirements"]

    karta_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="karta_pobytu",
    )
    replacement = await client.post(
        f"/api/v1/candidates/{candidate.id}/requirements/legal_stay_confirmation/replace-evidence",
        headers=manager_headers,
        json={"evidence_variant_code": "legal_stay_any"},
    )
    assert replacement.status_code == 200, replacement.text
    new_evidence_id = replacement.json()["evidence_id"]
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=new_evidence_id,
        document_id=karta_id,
    )
    approved = await approve_evidence_api(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=new_evidence_id,
    )
    assert approved["status"] == "approved"
    checklist_karta = await get_checklist(client, manager_headers, str(candidate.id))
    legal_after = next(
        row
        for row in checklist_karta["requirements"]
        if row["requirement_code"] == "legal_stay_confirmation"
    )
    assert legal_after["fulfilled"] is True
