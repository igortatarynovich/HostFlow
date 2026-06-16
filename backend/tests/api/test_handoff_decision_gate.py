from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff

_TRANSFER_POLICY_ASSERT = (
    "backend.app.services.transfer_policy_resolver.TransferPolicyResolver.assert_transfer_allowed"
)


@pytest.mark.anyio
async def test_ready_for_handoff_blocked_by_decision_contract(
    client: AsyncClient,
    manager_headers: dict[str, str],
    bootstrap: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Dec", "last_name": "Blocked", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 200, create.text
    candidate_id = create.json()["id"]
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    async def _blocked(*args, **kwargs):
        return {
            "code": "transfer_blocked",
            "message": "Transfer is blocked by transfer policy",
            "missing_types": ["work_permit"],
            "blocking_reasons": [{"code": "missing_required_document", "message": "work_permit missing"}],
        }

    monkeypatch.setattr(_TRANSFER_POLICY_ASSERT, _blocked)

    patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch.status_code == 409, patch.text
    detail = patch.json().get("detail") or {}
    assert detail.get("code") == "handoff_docs_incomplete"
    assert "work_permit" in (detail.get("missing_types") or [])


@pytest.mark.anyio
async def test_ready_for_handoff_allowed_when_decision_allows(
    client: AsyncClient,
    manager_headers: dict[str, str],
    bootstrap: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Dec", "last_name": "Allowed", "company_id": bootstrap["company_id"]},
    )
    assert create.status_code == 200, create.text
    candidate_id = create.json()["id"]
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    async def _allowed(*args, **kwargs):
        return {}

    monkeypatch.setattr(_TRANSFER_POLICY_ASSERT, _allowed)

    patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch.status_code == 200, patch.text
    assert str(patch.json().get("stage") or "").lower() == "ready_for_handoff"
