"""C2.2 PR-4 — Automation Engine HTTP API."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

REPO = Path(__file__).resolve().parents[2]
AUTOMATION_ROUTE = (
    REPO / "app" / "api" / "v1" / "communications" / "routes" / "automation.py"
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
    "emit_from_evaluation",
)


def test_automation_api_route_isolation():
    text = AUTOMATION_ROUTE.read_text(encoding="utf-8")
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
    assert "evaluate" in text  # dry-run uses pure evaluator
    assert offenders == [], f"PR-4 API isolation violated: {offenders}"


@pytest.mark.asyncio
async def test_automation_api_crud_publish_dry_run_decisions(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    key = f"c2_2_api_{uuid4().hex[:10]}"
    create = await client.post(
        "/api/v1/communications/automation/rules",
        headers=auth_headers,
        json={
            "key": key,
            "name": "API Rule",
            "intent_key": "manual_outbound",
            "channel": "email",
            "conditions": {"op": "eq", "path": "stage", "value": "interview"},
            "variables_mapping": {"name": {"literal": "Ada"}},
            "triggers": [
                {"event_type": "candidate.stage_changed", "event_filter": {}},
            ],
        },
    )
    assert create.status_code == 201, create.text
    created = create.json()
    rule_id = created["id"]
    assert created["key"] == key
    assert created["draft"] is not None
    assert created["latest_published"] is None

    listed = await client.get(
        "/api/v1/communications/automation/rules", headers=auth_headers
    )
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == rule_id for item in listed.json()["items"])

    patched = await client.patch(
        f"/api/v1/communications/automation/rules/{rule_id}/draft",
        headers=auth_headers,
        json={
            "conditions": {"op": "eq", "path": "stage", "value": "offer"},
            "triggers": [
                {"event_type": "candidate.stage_changed", "event_filter": {"source": "manual"}},
            ],
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["draft"]["conditions"]["value"] == "offer"

    draft_dry = await client.post(
        f"/api/v1/communications/automation/rules/{rule_id}/dry-run",
        headers=auth_headers,
        json={
            "event_id": "evt-dry-1",
            "event_type": "candidate.stage_changed",
            "data": {"stage": "offer", "source": "manual"},
        },
    )
    assert draft_dry.status_code == 200, draft_dry.text
    assert draft_dry.json()["outcome"] == "fire"
    assert "rule_not_published" not in draft_dry.json().get("reason_codes", [])

    published = await client.post(
        f"/api/v1/communications/automation/rules/{rule_id}/publish",
        headers=auth_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["latest_published"] is not None
    pub_id = published.json()["latest_published"]["id"]

    versions = await client.get(
        f"/api/v1/communications/automation/rules/{rule_id}/versions",
        headers=auth_headers,
    )
    assert versions.status_code == 200
    assert any(v["id"] == pub_id for v in versions.json()["items"])

    enabled = await client.post(
        f"/api/v1/communications/automation/rules/{rule_id}/enabled",
        headers=auth_headers,
        json={"enabled": False},
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is False

    await client.post(
        f"/api/v1/communications/automation/rules/{rule_id}/enabled",
        headers=auth_headers,
        json={"enabled": True},
    )

    # Seed a decision via domain helper path is not exposed; dry-run does not persist.
    # Publish path alone leaves decisions empty.
    decisions = await client.get(
        f"/api/v1/communications/automation/rules/{rule_id}/decisions",
        headers=auth_headers,
    )
    assert decisions.status_code == 200
    assert decisions.json()["items"] == []

    archived = await client.post(
        f"/api/v1/communications/automation/rules/{rule_id}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    active_list = await client.get(
        "/api/v1/communications/automation/rules", headers=auth_headers
    )
    assert all(item["id"] != rule_id for item in active_list.json()["items"])

    with_archived = await client.get(
        "/api/v1/communications/automation/rules",
        headers=auth_headers,
        params={"include_archived": True},
    )
    assert any(item["id"] == rule_id for item in with_archived.json()["items"])


@pytest.mark.asyncio
async def test_automation_api_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    missing = await client.get(
        f"/api/v1/communications/automation/rules/{uuid4()}",
        headers=auth_headers,
    )
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "rule_not_found"
