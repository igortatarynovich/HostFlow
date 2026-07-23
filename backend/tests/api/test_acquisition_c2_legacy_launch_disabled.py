"""C-2: no new searchAcquisition launches outside Campaign/Flight."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest
from httpx import AsyncClient

REPO = Path(__file__).resolve().parents[3]
DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"

# Only the hard-stop implementation may call/create legacy launches.
_BACKEND_CREATE_ALLOW = {
    Path("backend/app/services/search_acquisition_service.py"),
    Path("backend/app/api/v1/vacancies/acquisition_api.py"),
    Path("backend/tests/api/test_acquisition_c2_legacy_launch_disabled.py"),
}

# Create/launch only — not read-only hrefs like …/acquisition/activities list view.
_CREATE_PATTERNS = (
    re.compile(r"\badd_acquisition_activity\s*\("),
    re.compile(r"@router\.post\([^\n]*/acquisition/(?:activities|channels)"),
    re.compile(r"""(?:client|api)\.post\(\s*f?["'].*/acquisition/(?:activities|channels)(?!/)"""),
    re.compile(r"""["']action["']\s*:\s*["']duplicate["']"""),
)


def _headers(base: Dict[str, str]) -> Dict[str, str]:
    merged = dict(base)
    merged.setdefault("X-Tenant-Id", DEFAULT_TENANT_ID)
    merged.setdefault("Content-Type", "application/json")
    return merged


async def _first_company_id(client: AsyncClient, headers: Dict[str, str]) -> str:
    response = await client.get("/api/v1/companies?limit=1", headers=headers)
    response.raise_for_status()
    payload = response.json()
    items: List[Dict[str, Any]]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    else:
        raise AssertionError(f"Unexpected companies payload: {payload!r}")
    assert items
    return items[0]["id"]


async def _create_vacancy(client: AsyncClient, headers: Dict[str, str]) -> str:
    company_id = await _first_company_id(client, headers)
    resp = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": f"[c2] legacy launch {uuid.uuid4().hex[:8]}",
            "status": "open",
            "employment_type": "full_time",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


@pytest.mark.anyio
async def test_post_acquisition_activity_returns_410(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    vacancy_id = await _create_vacancy(client, headers)
    for suffix in ("activities", "channels"):
        resp = await client.post(
            f"/api/v1/vacancies/{vacancy_id}/acquisition/{suffix}",
            headers=headers,
            json={"type": "meta", "name": "Should not create"},
        )
        assert resp.status_code == 410, resp.text
        detail = resp.json()["detail"]
        assert detail["code"] == "legacy_launch_disabled"
        assert detail["marketing_setup_path"].startswith("/app/marketing/new?")
        assert f"target_id={vacancy_id}" in detail["marketing_setup_path"]


@pytest.mark.anyio
async def test_duplicate_action_returns_410(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    vacancy_id = await _create_vacancy(client, headers)
    # Seed a legacy activity directly in vacancy.extra via GET snapshot path is empty;
    # duplicate on missing id is 404 — seed via SQL-less PATCH of vacancy extra.
    get_vac = await client.get(f"/api/v1/vacancies/{vacancy_id}", headers=headers)
    assert get_vac.status_code == 200
    import json

    from backend.app.db.session import async_session_maker
    from backend.app.models.vacancy import Vacancy
    from sqlalchemy import select

    activity_id = f"act_meta_{uuid.uuid4().hex[:8]}"
    async with async_session_maker() as session:
        row = (
            await session.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
        ).scalar_one()
        extra = json.loads(row.extra) if row.extra else {}
        block = {
            "version": 2,
            "activities": [
                {
                    "id": activity_id,
                    "channel_type": "meta",
                    "type": "meta",
                    "name": "Legacy seed",
                    "search_ids": [vacancy_id],
                    "lifecycle": "active",
                    "status": "active",
                }
            ],
        }
        block["channels"] = block["activities"]
        extra["acquisition_v1"] = block
        row.extra = json.dumps(extra, ensure_ascii=False)
        await session.commit()

    resp = await client.post(
        f"/api/v1/vacancies/{vacancy_id}/acquisition/activities/{activity_id}/actions",
        headers=headers,
        json={"action": "duplicate"},
    )
    assert resp.status_code == 410, resp.text
    assert resp.json()["detail"]["code"] == "legacy_launch_disabled"


@pytest.mark.anyio
async def test_snapshot_exposes_legacy_reconciliation(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    vacancy_id = await _create_vacancy(client, headers)
    resp = await client.get(f"/api/v1/vacancies/{vacancy_id}/acquisition", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["legacy_mode"] is True
    assert body["reconciliation"]["status"] == "unresolved"
    assert body["marketing_setup_path"].startswith("/app/marketing/new?")


def test_backend_scan_no_hidden_legacy_launch_call_sites() -> None:
    """Mandatory C-2 scan: no hidden searchAcquisition create/launch call sites."""
    roots = [
        REPO / "backend" / "app",
        REPO / "backend" / "tests",
    ]
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            rel = path.relative_to(REPO)
            if rel in _BACKEND_CREATE_ALLOW:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in _CREATE_PATTERNS:
                if pattern.search(text):
                    offenders.append(f"{rel}: matched {pattern.pattern}")
    assert not offenders, "Hidden legacy launch paths:\n" + "\n".join(offenders)


def test_legacy_launch_flag_is_on() -> None:
    from backend.app.services.search_acquisition_service import LEGACY_LAUNCH_DISABLED

    assert LEGACY_LAUNCH_DISABLED is True


def test_service_create_raises_without_persist() -> None:
    import asyncio

    from backend.app.services.search_acquisition_service import (
        LegacyLaunchDisabledError,
        add_acquisition_activity,
    )

    class _Vac:
        id = "vac-1"
        title = "Cook"

    async def _run() -> None:
        with pytest.raises(LegacyLaunchDisabledError) as exc:
            await add_acquisition_activity(
                None,  # type: ignore[arg-type]
                "t1",
                _Vac(),  # type: ignore[arg-type]
                channel_type="meta",
                name="Nope",
            )
        assert exc.value.marketing_setup_path.startswith("/app/marketing/new?")

    asyncio.run(_run())
