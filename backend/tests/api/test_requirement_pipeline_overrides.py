"""Phase 3c: requirement-centric pipeline waivers."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import (
    approve_evidence_api,
    link_evidence_document,
    post_document,
    select_evidence,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _noop_rodo(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "backend.app.api.v1.candidates.service._enforce_rodo_before_contact_stage",
        _noop,
    )


async def _move_to_docs_wait(client: AsyncClient, headers: dict[str, str], candidate_id: str) -> None:
    for stage in ("contacted", "questionnaire_submitted", "docs_wait"):
        resp = await client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={"stage": stage},
        )
        assert resp.status_code == 200, resp.text


async def test_requirement_waiver_allows_pipeline_forward(
    client: AsyncClient,
    manager_headers: dict[str, str],
    supervisor_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    await _move_to_docs_wait(client, manager_headers, str(candidate.id))

    cid = str(candidate.id)
    for requirement_code, variant_code, doc_type in (
        ("identity_document", "identity_any", "passport"),
        ("tachograph_card", "tacho_any", "tachograph_card"),
    ):
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

    blocked = await client.patch(
        f"/api/v1/candidates/{candidate.id}",
        headers=manager_headers,
        json={"stage": "docs_got"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "stage_blocked_by_requirements"
    assert "driver_license_with_code95" in (blocked.json()["detail"].get("missing_requirements") or [])

    created = await client.post(
        f"/api/v1/candidates/{candidate.id}/pipeline-overrides",
        headers=manager_headers,
        json={
            "requirement_code": "driver_license_with_code95",
            "reason": "Client confirmed license will arrive next week",
            "requested_scope": "pipeline",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["requirement_code"] == "driver_license_with_code95"
    assert body.get("doc_type_code") in (None, "")

    override_id = body["id"]
    approved = await client.post(
        f"/api/v1/candidates/{candidate.id}/pipeline-overrides/{override_id}/approve",
        headers=supervisor_headers,
        json={"granted_scope": "pipeline", "review_note": "Approved for pipeline only"},
    )
    assert approved.status_code == 200, approved.text

    forward = await client.patch(
        f"/api/v1/candidates/{candidate.id}",
        headers=manager_headers,
        json={"stage": "docs_got"},
    )
    assert forward.status_code == 200, forward.text


async def test_identity_requirement_not_waivable(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    resp = await client.post(
        f"/api/v1/candidates/{candidate.id}/pipeline-overrides",
        headers=manager_headers,
        json={
            "requirement_code": "identity_document",
            "reason": "Should never be allowed to waive identity gate",
            "requested_scope": "pipeline",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "requirement_not_overridable"


async def test_work_panel_includes_requirement_blockers_not_visa_karta_split(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    resp = await client.get(
        f"/api/v1/candidates/{candidate.id}/work-panel",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    rs = data.get("requirements_summary")
    assert rs is not None
    pb = rs.get("pipeline_blockers") or {}
    missing = pb.get("missing_requirements") or []
    assert missing.count("legal_stay_confirmation") == 1
    assert "visa" not in missing
    assert "karta_pobytu" not in missing
    items = rs.get("items") or []
    codes = [row["requirement_code"] for row in items]
    assert "legal_stay_confirmation" in codes
    assert len(items) == 4
