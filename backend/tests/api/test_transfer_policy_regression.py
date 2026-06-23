"""Transfer Policy API regression — stage gate + transfer-readiness contract."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff

_RESOLVE = "backend.app.services.transfer_policy_resolver.TransferPolicyResolver.resolve"
_ASSERT = "backend.app.process_engine.evaluator_adapter.TransitionEvaluatorAdapter.assert_transition_allowed"


@pytest.mark.anyio
async def test_transfer_readiness_endpoint_returns_policy_contract(
    client: AsyncClient,
    manager_headers: dict[str, str],
    bootstrap: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Tr", "last_name": "Readiness", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 200, create.text
    candidate_id = create.json()["id"]

    async def _report(*args, **kwargs):
        return {
            "candidate_id": candidate_id,
            "policy_version": "transfer_policy_v1",
            "transfer_allowed": False,
            "handoff_create_allowed": False,
            "destinations_allowed": [],
            "blocking_reasons": [
                {
                    "code": "missing_required_document",
                    "message": "Required document 'work_permit' is missing.",
                    "source_layer": "document_packs",
                }
            ],
            "warnings": [],
            "required_documents": ["work_permit"],
            "missing_documents": ["work_permit"],
            "pending_verification_documents": [],
            "missing_data_fields": [],
            "required_confirmations": [],
            "approved_overrides": [],
            "source_layers": ["document_packs"],
        }

    monkeypatch.setattr(_RESOLVE, _report)

    resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/transfer-readiness",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["policy_version"] == "transfer_policy_v1"
    assert body["transfer_allowed"] is False
    assert body["blocking_reasons"][0]["source_layer"] == "document_packs"


@pytest.mark.anyio
async def test_stage_change_blocked_until_transfer_policy_allows(
    client: AsyncClient,
    manager_headers: dict[str, str],
    bootstrap: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Tr", "last_name": "Blocked", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 200, create.text
    candidate_id = create.json()["id"]
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    state = {"allowed": False}

    async def _assert(*args, **kwargs):
        if state["allowed"]:
            return {}
        return {
            "code": "transfer_blocked",
            "message": "Transfer is blocked by transfer policy",
            "missing_types": ["work_permit"],
            "blocking_reasons": [
                {
                    "code": "missing_required_document",
                    "message": "Required document 'work_permit' is missing.",
                    "source_layer": "document_packs",
                }
            ],
            "source_layers": ["document_packs"],
        }

    monkeypatch.setattr(_ASSERT, _assert)

    blocked = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert blocked.status_code == 409, blocked.text
    detail = blocked.json().get("detail") or {}
    assert detail.get("code") == "handoff_docs_incomplete"
    assert "work_permit" in (detail.get("missing_types") or [])

    state["allowed"] = True
    allowed = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert allowed.status_code == 200, allowed.text
    assert str(allowed.json().get("stage") or "").lower() == "ready_for_handoff"


@pytest.mark.anyio
async def test_transfer_readiness_available_on_processing_by_hr_stage(
    client: AsyncClient,
    manager_headers: dict[str, str],
    bootstrap: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Tr", "last_name": "HrStage", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 200, create.text
    candidate_id = create.json()["id"]

    calls: list[str] = []

    async def _report(db, *, tenant_id, candidate_id, target_stage=None, require_destination=False):
        calls.append(str(target_stage or ""))
        return {
            "candidate_id": candidate_id,
            "policy_version": "transfer_policy_v1",
            "transfer_allowed": True,
            "handoff_create_allowed": False,
            "destinations_allowed": [],
            "blocking_reasons": [],
            "warnings": [{"code": "no_destination", "message": "No handoff destination", "source_layer": "tenant_link"}],
            "required_documents": [],
            "missing_documents": [],
            "pending_verification_documents": [],
            "missing_data_fields": [],
            "required_confirmations": [],
            "approved_overrides": [],
            "source_layers": ["document_packs", "tenant_link"],
        }

    monkeypatch.setattr(_RESOLVE, _report)

    to_hr = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "processing_by_hr"},
    )
    assert to_hr.status_code in {200, 409}, to_hr.text

    resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/transfer-readiness",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["transfer_allowed"] is True
    assert body["handoff_create_allowed"] is False
    assert len(calls) >= 1


@pytest.mark.anyio
async def test_recruitment_package_backward_compat_embeds_transfer_summary(
    client: AsyncClient,
    manager_headers: dict[str, str],
    bootstrap: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Tr", "last_name": "LegacyPkg", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 200, create.text
    candidate_id = create.json()["id"]

    async def _report(*args, **kwargs):
        return {
            "candidate_id": candidate_id,
            "policy_version": "transfer_policy_v1",
            "transfer_allowed": False,
            "handoff_create_allowed": False,
            "handoff_allowed": True,
            "destinations_allowed": ["internal_hr"],
            "blocking_reasons": [],
            "warnings": [],
            "required_documents": ["passport"],
            "missing_documents": [],
            "pending_verification_documents": [],
            "missing_data_fields": [],
            "required_confirmations": [],
            "approved_overrides": [],
            "source_layers": ["document_packs"],
            "blocking_blocks": [],
            "blocks": [],
            "ready": False,
        }

    monkeypatch.setattr(_RESOLVE, _report)

    resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/recruitment-package",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "ready" in body
    assert body.get("transfer_readiness", {}).get("transfer_allowed") is False
