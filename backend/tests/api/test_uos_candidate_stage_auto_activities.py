from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

CANDIDATES_BASE = "/api/v1/candidates"
REMINDERS_BASE = "/api/v1/reminders"


@pytest.mark.anyio
async def test_uos_candidate_stage_follow_up_on_patch(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    create_resp = await client.post(
        CANDIDATES_BASE,
        headers=manager_headers,
        json={"first_name": "UOS", "last_name": "StageAuto"},
    )
    assert create_resp.status_code == 200, create_resp.text
    cand = create_resp.json()
    cid = str(cand["id"])

    r0 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "candidate", "entity_id": cid, "type_filter": "uos_candidate_stage_follow_up"},
    )
    assert r0.status_code == 200, r0.text
    assert len(r0.json().get("items") or []) == 0

    patch_a = await client.patch(
        f"{CANDIDATES_BASE}/{cid}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )
    assert patch_a.status_code == 200, patch_a.text

    r_stage = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "candidate", "entity_id": cid, "type_filter": "uos_candidate_stage_follow_up"},
    )
    assert r_stage.status_code == 200, r_stage.text
    stage_items = r_stage.json().get("items") or []
    assert len(stage_items) == 1
    assert stage_items[0]["type"] == "uos_candidate_stage_follow_up"
    assert stage_items[0]["entity_type"] == "candidate"
    assert stage_items[0]["entity_id"] == cid
    assert "contacted" in (stage_items[0].get("title") or "")
    first_id = stage_items[0]["id"]

    patch_b = await client.patch(
        f"{CANDIDATES_BASE}/{cid}",
        headers=manager_headers,
        json={"stage": "docs_wait"},
    )
    assert patch_b.status_code == 200, patch_b.text

    r_stage2 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "candidate", "entity_id": cid, "type_filter": "uos_candidate_stage_follow_up"},
    )
    stage_items2 = r_stage2.json().get("items") or []
    assert len(stage_items2) == 1
    assert stage_items2[0]["id"] == first_id
    assert "docs_wait" in (stage_items2[0].get("title") or "")
