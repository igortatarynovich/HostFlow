"""C2.3 PR-5 — Campaign Orchestrator HTTP API."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

REPO = Path(__file__).resolve().parents[2]
CAMPAIGN_ROUTE = (
    REPO / "app" / "api" / "v1" / "communications" / "routes" / "campaigns.py"
)

FORBIDDEN_MODULE_IMPORT_PREFIXES = (
    "backend.app.modules.recruitment",
    "backend.app.modules.sales",
    "backend.app.modules.hr",
    "backend.app.modules.services",
    "backend.app.modules.finance",
)

FORBIDDEN_SEND_PATH_TOKENS = (
    "CommunicationSender",
    "dispatch_message",
    "send_email",
    "execute_communication_intent",
)


def test_campaign_api_route_isolation():
    text = CAMPAIGN_ROUTE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_MODULE_IMPORT_PREFIXES):
                offenders.append(f"from {mod}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if any(name == p or name.startswith(p + ".") for p in FORBIDDEN_MODULE_IMPORT_PREFIXES):
                    offenders.append(f"import {name}")
    for token in FORBIDDEN_SEND_PATH_TOKENS:
        if token in text:
            offenders.append(f"token:{token}")
    assert "execute_campaign_run" in text
    assert "audience_dry_run" in text or "dry_run" in text
    assert offenders == [], f"PR-5 API isolation violated: {offenders}"


@pytest.mark.asyncio
async def test_campaign_api_crud_publish_run_execute(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    key = f"c2_3_api_{uuid4().hex[:10]}"
    create = await client.post(
        "/api/v1/communications/campaigns",
        headers=auth_headers,
        json={
            "key": key,
            "name": "API Campaign",
            "intent_key": "follow_up",
            "channel": "email",
            "audience": {
                "definition_type": "static_list",
                "definition": {
                    "recipients": [
                        {
                            "entity_type": "candidate",
                            "entity_id": "c-1",
                            "address": "api@example.com",
                            "snapshot": {"name": "Api"},
                        }
                    ]
                },
            },
        },
    )
    assert create.status_code == 201, create.text
    created = create.json()
    campaign_id = created["id"]
    assert created["key"] == key
    assert created["draft"] is not None
    assert created["latest_published"] is None
    assert created["draft"]["audience_definition"]["definition_type"] == "static_list"

    listed = await client.get(
        "/api/v1/communications/campaigns", headers=auth_headers
    )
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == campaign_id for item in listed.json()["items"])

    patched = await client.patch(
        f"/api/v1/communications/campaigns/{campaign_id}/draft",
        headers=auth_headers,
        json={
            "intent_key": "follow_up",
            "audience": {
                "definition_type": "static_list",
                "definition": {
                    "recipients": [
                        {
                            "entity_type": "candidate",
                            "entity_id": "c-1",
                            "address": "api@example.com",
                        },
                        {
                            "entity_type": "candidate",
                            "entity_id": "c-2",
                            "address": "two@example.com",
                        },
                    ]
                },
            },
        },
    )
    assert patched.status_code == 200, patched.text
    assert (
        len(patched.json()["draft"]["audience_definition"]["definition"]["recipients"])
        == 2
    )

    dry = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/audience/dry-run",
        headers=auth_headers,
        json={},
    )
    assert dry.status_code == 200, dry.text
    assert dry.json()["ok"] is True
    assert len(dry.json()["recipients"]) == 2

    published = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/publish",
        headers=auth_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["latest_published"] is not None
    pub_id = published.json()["latest_published"]["id"]

    versions = await client.get(
        f"/api/v1/communications/campaigns/{campaign_id}/versions",
        headers=auth_headers,
    )
    assert versions.status_code == 200
    assert any(v["id"] == pub_id for v in versions.json()["items"])

    idem = f"api-run-{uuid4().hex}"
    run_create = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/runs",
        headers=auth_headers,
        json={"idempotency_key": idem},
    )
    assert run_create.status_code == 201, run_create.text
    run = run_create.json()
    run_id = run["id"]
    assert run["campaign_version_id"] == pub_id
    assert run["status"] == "pending"
    assert len(run["recipients"]) == 2
    assert len(run["items"]) == 2

    # Idempotent create
    run_again = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/runs",
        headers=auth_headers,
        json={"idempotency_key": idem},
    )
    assert run_again.status_code == 201
    assert run_again.json()["id"] == run_id

    executed = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/runs/{run_id}/execute",
        headers=auth_headers,
        json={"mode": "request_only"},
    )
    assert executed.status_code == 200, executed.text
    body = executed.json()
    assert body["orchestration"]["status"] == "completed"
    assert body["orchestration"]["summary"]["emitted"] == 2
    assert body["run"]["status"] == "completed"
    assert all(i["status"] == "emitted" for i in body["run"]["items"])

    got = await client.get(
        f"/api/v1/communications/campaigns/{campaign_id}/runs/{run_id}",
        headers=auth_headers,
    )
    assert got.status_code == 200
    assert got.json()["status"] == "completed"

    runs = await client.get(
        f"/api/v1/communications/campaigns/{campaign_id}/runs",
        headers=auth_headers,
    )
    assert runs.status_code == 200
    assert any(r["id"] == run_id for r in runs.json()["items"])


@pytest.mark.asyncio
async def test_campaign_api_cancel_pending_run(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    key = f"c2_3_cancel_{uuid4().hex[:10]}"
    create = await client.post(
        "/api/v1/communications/campaigns",
        headers=auth_headers,
        json={
            "key": key,
            "name": "Cancel Campaign",
            "intent_key": "follow_up",
            "audience": {
                "definition_type": "static_list",
                "definition": {
                    "recipients": [
                        {
                            "entity_type": "candidate",
                            "entity_id": "x",
                            "address": "x@example.com",
                        }
                    ]
                },
            },
        },
    )
    assert create.status_code == 201, create.text
    campaign_id = create.json()["id"]
    pub = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/publish",
        headers=auth_headers,
    )
    assert pub.status_code == 200, pub.text
    run_create = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/runs",
        headers=auth_headers,
        json={"idempotency_key": f"cancel-{uuid4().hex}"},
    )
    assert run_create.status_code == 201, run_create.text
    run_id = run_create.json()["id"]

    cancelled = await client.post(
        f"/api/v1/communications/campaigns/{campaign_id}/runs/{run_id}/cancel",
        headers=auth_headers,
        json={"reason": "operator"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
