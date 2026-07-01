"""Document list visibility by ``X-Document-Viewer-Channel`` (ADR-014 primary scope, no dossier_zone in response)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from backend.tests.conftest import _init_data


def _db_headers(base: dict[str, str], *, channel: str) -> dict[str, str]:
    return {**base, "X-Document-Viewer-Channel": channel}


@pytest.mark.anyio
async def test_viewer_channel_filters_db_candidate_documents(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    """
    Recruitment viewer: passport + shared driver_license; not HR-only medical nor transport-only code95.
    Transport viewer: shared driver_license + transport code95; not recruitment-scoped passport.
    HR viewer: HR medical + shared driver_license; not recruitment-only passport.
    """
    data = await _init_data()
    company_id = data["company_id"]

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "Viewer",
            "last_name": f"V{tag}",
            "company_id": company_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    issued = (date.today() - timedelta(days=200)).isoformat()
    expires = (date.today() + timedelta(days=500)).isoformat()

    async def post_db(payload: dict) -> dict:
        r = await client.post(
            f"/api/v1/db/candidate/{candidate_id}/documents",
            headers=manager_headers,
            json=payload,
        )
        if r.status_code == 402:
            detail = r.json().get("detail")
            if isinstance(detail, dict) and detail.get("code") == "document_limit_reached":
                pytest.skip("Test tenant at document quota")
        assert r.status_code == 201, r.text
        return r.json()

    passport = await post_db(
        {
            "type": "passport",
            "number": f"PP-{tag}",
            "issued_at": issued,
            "expires_at": expires,
            "extra": {"country": "PL"},
        }
    )
    dl = await post_db(
        {
            "type": "driver_license",
            "number": f"DL-{tag}",
            "expires_at": expires,
            "status": "received",
            "extra": {"title": "DL"},
        }
    )
    med = await post_db(
        {
            "type": "medical_certificate",
            "status": "missing",
            "extra": {"title": "Medical"},
        }
    )
    c95 = await post_db(
        {
            "type": "code95",
            "status": "missing",
            "extra": {"title": "Code95"},
        }
    )

    pid, did, mid, cid = passport["id"], dl["id"], med["id"], c95["id"]

    async def list_ids(channel: str) -> set[str]:
        r = await client.get(
            f"/api/v1/db/candidate/{candidate_id}/documents",
            headers=_db_headers(manager_headers, channel=channel),
            params={"fill_missing": "false"},
        )
        assert r.status_code == 200, r.text
        return {d["id"] for d in r.json()}

    rec_ids = await list_ids("recruitment")
    assert pid in rec_ids and did in rec_ids
    assert mid not in rec_ids and cid not in rec_ids

    tr_ids = await list_ids("transport")
    assert did in tr_ids and cid in tr_ids
    assert pid not in tr_ids and mid not in tr_ids

    hr_ids = await list_ids("hr")
    assert mid in hr_ids and did in hr_ids
    assert pid not in hr_ids and cid not in hr_ids

    g_med_rec = await client.get(
        f"/api/v1/db/documents/{mid}",
        headers=_db_headers(manager_headers, channel="recruitment"),
    )
    assert g_med_rec.status_code == 404, g_med_rec.text

    g_pp_tr = await client.get(
        f"/api/v1/db/documents/{pid}",
        headers=_db_headers(manager_headers, channel="transport"),
    )
    assert g_pp_tr.status_code == 404, g_pp_tr.text
