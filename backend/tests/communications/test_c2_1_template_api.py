"""C2.1 PR-4 — Template Platform HTTP API."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

REPO = Path(__file__).resolve().parents[2]
TEMPLATES_ROUTE = (
    REPO / "app" / "api" / "v1" / "communications" / "routes" / "templates.py"
)

FORBIDDEN_MODULE_IMPORT_PREFIXES = (
    "backend.app.modules.recruitment",
    "backend.app.modules.sales",
    "backend.app.modules.hr",
    "backend.app.modules.services",
    "backend.app.modules.finance",
    "app.modules.recruitment",
    "app.modules.sales",
    "app.modules.hr",
    "app.modules.services",
    "app.modules.finance",
)

FORBIDDEN_SEND_PATH_TOKENS = (
    "CommunicationSender",
    "dispatch_message",
    "send_email",
)


def test_template_api_route_capability_isolation():
    tree = ast.parse(TEMPLATES_ROUTE.read_text(encoding="utf-8"))
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
    text = TEMPLATES_ROUTE.read_text(encoding="utf-8")
    for token in FORBIDDEN_SEND_PATH_TOKENS:
        if token in text:
            offenders.append(f"token:{token}")
    assert offenders == [], f"PR-4 API isolation violated: {offenders}"


@pytest.mark.asyncio
async def test_template_api_crud_publish_preview_versions_diff(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    key = f"c2_1_api_{uuid4().hex[:10]}"
    create = await client.post(
        "/api/v1/communications/templates",
        headers=auth_headers,
        json={
            "key": key,
            "name": "API Template",
            "description": "PR-4 smoke",
            "locale": "pl",
            "subject": "Hello {{name}}",
            "body_text": "Hi {{name}}",
            "channels": ["email"],
            "intent_keys": ["manual_outbound"],
            "variables": [
                {
                    "name": "name",
                    "var_type": "string",
                    "required": True,
                    "description": "Recipient name",
                }
            ],
        },
    )
    assert create.status_code == 201, create.text
    created = create.json()
    template_id = created["id"]
    assert created["key"] == key
    assert created["draft"] is not None
    draft_id = created["draft"]["id"]
    assert created["latest_published"] is None

    listed = await client.get("/api/v1/communications/templates", headers=auth_headers)
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == template_id for item in listed.json()["items"])

    patched = await client.patch(
        f"/api/v1/communications/templates/{template_id}/draft",
        headers=auth_headers,
        json={
            "subject": "Cześć {{name}}",
            "body_text": "Witaj {{name}} — draft",
            "variables": [
                {
                    "name": "name",
                    "var_type": "string",
                    "required": True,
                },
                {
                    "name": "extra",
                    "var_type": "string",
                    "required": False,
                    "default_value": "x",
                },
            ],
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["draft"]["subject"] == "Cześć {{name}}"
    assert {v["name"] for v in patched.json()["draft"]["variables"]} == {"name", "extra"}

    draft_preview = await client.post(
        f"/api/v1/communications/templates/{template_id}/preview",
        headers=auth_headers,
        json={
            "version_id": draft_id,
            "channel": "email",
            "variables": {"name": "Ada", "extra": "y"},
        },
    )
    assert draft_preview.status_code == 200, draft_preview.text
    preview_body = draft_preview.json()
    assert preview_body.get("ok") is True or preview_body.get("subject") or preview_body.get(
        "body_text"
    )
    # Draft preview must not fail solely on template_not_published.
    codes = {d.get("code") for d in (preview_body.get("diagnostics") or [])}
    assert "template_not_published" not in codes

    published = await client.post(
        f"/api/v1/communications/templates/{template_id}/publish",
        headers=auth_headers,
    )
    assert published.status_code == 200, published.text
    pub = published.json()
    assert pub["latest_published"] is not None
    published_version_id = pub["latest_published"]["id"]
    assert pub["published_version"]["id"] == published_version_id
    assert pub["draft"] is not None
    assert pub["draft"]["id"] != published_version_id

    # Second edit + publish for a meaningful diff.
    await client.patch(
        f"/api/v1/communications/templates/{template_id}/draft",
        headers=auth_headers,
        json={"body_text": "Witaj {{name}} — v2"},
    )
    published2 = await client.post(
        f"/api/v1/communications/templates/{template_id}/publish",
        headers=auth_headers,
    )
    assert published2.status_code == 200, published2.text
    v2_id = published2.json()["latest_published"]["id"]

    versions = await client.get(
        f"/api/v1/communications/templates/{template_id}/versions",
        headers=auth_headers,
    )
    assert versions.status_code == 200, versions.text
    version_ids = {item["id"] for item in versions.json()["items"]}
    assert published_version_id in version_ids
    assert v2_id in version_ids

    one = await client.get(
        f"/api/v1/communications/templates/{template_id}/versions/{published_version_id}",
        headers=auth_headers,
    )
    assert one.status_code == 200, one.text
    assert one.json()["id"] == published_version_id

    diff = await client.get(
        f"/api/v1/communications/templates/{template_id}/diff",
        headers=auth_headers,
        params={"from": published_version_id, "to": v2_id},
    )
    assert diff.status_code == 200, diff.text
    diff_body = diff.json()
    assert diff_body["identical"] is False
    assert "body_text" in diff_body["changed"]

    pub_preview = await client.post(
        f"/api/v1/communications/templates/{template_id}/preview",
        headers=auth_headers,
        json={"channel": "email", "variables": {"name": "Ada", "extra": "y"}},
    )
    assert pub_preview.status_code == 200, pub_preview.text

    archived = await client.post(
        f"/api/v1/communications/templates/{template_id}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    active_list = await client.get("/api/v1/communications/templates", headers=auth_headers)
    assert active_list.status_code == 200
    assert all(item["id"] != template_id for item in active_list.json()["items"])

    with_archived = await client.get(
        "/api/v1/communications/templates",
        headers=auth_headers,
        params={"include_archived": True},
    )
    assert with_archived.status_code == 200
    assert any(item["id"] == template_id for item in with_archived.json()["items"])


@pytest.mark.asyncio
async def test_template_api_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    missing = await client.get(
        f"/api/v1/communications/templates/{uuid4()}",
        headers=auth_headers,
    )
    assert missing.status_code == 404
    detail = missing.json()["detail"]
    assert detail["code"] == "template_not_found"
