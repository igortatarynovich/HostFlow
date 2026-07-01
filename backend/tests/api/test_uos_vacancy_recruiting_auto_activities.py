"""UOS: vacancy enters recruiting → deduped follow-up reminder."""

from __future__ import annotations

from typing import Dict
from uuid import UUID

import pytest
from httpx import AsyncClient

VAC_BASE = "/api/v1/vacancies"
COMPANY_BASE = "/api/v1/companies"
REMINDERS_BASE = "/api/v1/reminders"


def _uuid(s: str) -> UUID:
    return UUID(str(s))


async def _first_company_id(client: AsyncClient, headers: Dict[str, str]) -> str:
    r = await client.get(f"{COMPANY_BASE}/?limit=1", headers=headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    items = payload if isinstance(payload, list) else (payload.get("items") or [])
    assert items
    return str(items[0].get("id") or items[0].get("uuid"))


@pytest.mark.anyio
async def test_uos_vacancy_recruiting_follow_up_on_create_and_reopen(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    company_id = await _first_company_id(client, manager_headers)

    closed = await client.post(
        VAC_BASE,
        headers=manager_headers,
        json={
            "company_id": company_id,
            "title": "UOS vacancy closed on create",
            "status": "closed",
            "employment_type": "full_time",
        },
    )
    assert closed.status_code == 200, closed.text
    vid_closed = str(closed.json()["id"])

    r0 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "vacancy", "entity_id": vid_closed, "type_filter": "uos_vacancy_recruiting_follow_up"},
    )
    assert r0.status_code == 200, r0.text
    assert len(r0.json().get("items") or []) == 0

    open_v = await client.post(
        VAC_BASE,
        headers=manager_headers,
        json={
            "company_id": company_id,
            "title": "UOS vacancy open on create",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert open_v.status_code == 200, open_v.text
    vid_open = str(open_v.json()["id"])

    r1 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "vacancy", "entity_id": vid_open, "type_filter": "uos_vacancy_recruiting_follow_up"},
    )
    assert r1.status_code == 200, r1.text
    items1 = r1.json().get("items") or []
    assert len(items1) == 1
    assert items1[0]["type"] == "uos_vacancy_recruiting_follow_up"
    assert "UOS vacancy open" in (items1[0].get("title") or "")
    rid = items1[0]["id"]

    title_only = await client.patch(
        f"{VAC_BASE}/{_uuid(vid_open)}",
        headers=manager_headers,
        json={"title": "UOS vacancy open on create — renamed"},
    )
    assert title_only.status_code == 200, title_only.text

    r2 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "vacancy", "entity_id": vid_open, "type_filter": "uos_vacancy_recruiting_follow_up"},
    )
    items2 = r2.json().get("items") or []
    assert len(items2) == 1
    assert items2[0]["id"] == rid

    to_closed = await client.patch(
        f"{VAC_BASE}/{_uuid(vid_open)}",
        headers=manager_headers,
        json={"is_open": False},
    )
    assert to_closed.status_code == 200, to_closed.text

    reopen = await client.patch(
        f"{VAC_BASE}/{_uuid(vid_open)}",
        headers=manager_headers,
        json={"is_open": True},
    )
    assert reopen.status_code == 200, reopen.text

    r3 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "vacancy", "entity_id": vid_open, "type_filter": "uos_vacancy_recruiting_follow_up"},
    )
    items3 = r3.json().get("items") or []
    assert len(items3) == 1
    assert "renamed" in (items3[0].get("title") or "") or "UOS vacancy" in (items3[0].get("title") or "")
