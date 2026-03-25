from __future__ import annotations

from typing import Dict
from uuid import UUID

import pytest
from httpx import AsyncClient

COMPANY_BASE = "/api/v1/companies"
REMINDERS_BASE = "/api/v1/reminders"


def _uuid(s: str) -> UUID:
    return UUID(str(s))


@pytest.mark.anyio
async def test_uos_client_company_intro_and_stage_follow_up(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    create_resp = await client.post(
        f"{COMPANY_BASE}/",
        headers=manager_headers,
        json={"name": "UOS Client AutoCo", "company_role": "client"},
    )
    assert create_resp.status_code == 200, create_resp.text
    company = create_resp.json()
    cid = str(company["id"])

    r_intro = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "company", "entity_id": cid, "type_filter": "uos_client_intro"},
    )
    assert r_intro.status_code == 200, r_intro.text
    intro_items = r_intro.json().get("items") or []
    assert len(intro_items) == 1
    assert intro_items[0]["type"] == "uos_client_intro"
    assert intro_items[0]["entity_type"] == "company"
    assert intro_items[0]["entity_id"] == cid

    patch_a = await client.patch(
        f"{COMPANY_BASE}/{_uuid(cid)}",
        headers=manager_headers,
        json={"client_stage": "discovery"},
    )
    assert patch_a.status_code == 200, patch_a.text

    r_stage = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "company", "entity_id": cid, "type_filter": "uos_client_stage_follow_up"},
    )
    assert r_stage.status_code == 200, r_stage.text
    stage_items = r_stage.json().get("items") or []
    assert len(stage_items) == 1
    assert stage_items[0]["type"] == "uos_client_stage_follow_up"
    assert "discovery" in (stage_items[0].get("title") or "")
    first_id = stage_items[0]["id"]

    patch_b = await client.patch(
        f"{COMPANY_BASE}/{_uuid(cid)}",
        headers=manager_headers,
        json={"client_stage": "negotiation"},
    )
    assert patch_b.status_code == 200, patch_b.text

    r_stage2 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "company", "entity_id": cid, "type_filter": "uos_client_stage_follow_up"},
    )
    stage_items2 = r_stage2.json().get("items") or []
    assert len(stage_items2) == 1
    assert stage_items2[0]["id"] == first_id
    assert "negotiation" in (stage_items2[0].get("title") or "")

    patch_term = await client.patch(
        f"{COMPANY_BASE}/{_uuid(cid)}",
        headers=manager_headers,
        json={"client_stage": "rejected"},
    )
    assert patch_term.status_code == 200, patch_term.text

    r_stage3 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "company", "entity_id": cid, "type_filter": "uos_client_stage_follow_up"},
    )
    stage_items3 = r_stage3.json().get("items") or []
    assert len(stage_items3) == 1
    assert stage_items3[0]["id"] == first_id
