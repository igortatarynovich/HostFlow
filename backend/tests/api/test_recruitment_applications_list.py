"""GET /recruitment/applications — recruitment inbox list."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Lead, OwnCompany
from backend.tests.api.test_leads_meta import _ensure_company


@pytest.mark.anyio
async def test_list_recruitment_applications_includes_duplicate_review_lead(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    """Regression: duplicate_review leads must not break LeadOut serialization."""
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        oc_row = await db.execute(
            select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()).limit(1)
        )
        own_company_id = oc_row.scalar_one_or_none()
        if own_company_id is None:
            own_company_id = str(uuid.uuid4())
            db.add(
                OwnCompany(
                    id=own_company_id,
                    tenant_id=tenant_id,
                    name="Test OC",
                )
            )
            await db.commit()

        lead_id = str(uuid.uuid4())
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=str(own_company_id),
                company_id=str(company_id),
                source="website",
                status="duplicate_review",
                lead_type="candidate",
                payload={"name": "Dup Review Lead"},
            )
        )
        await db.commit()

    resp = await client.get(
        "/api/v1/recruitment/applications",
        headers=manager_headers,
        params={"limit": 50},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids = {item["id"] for item in body.get("items", [])}
    assert str(lead_id) in ids
    row = next(item for item in body["items"] if item["id"] == str(lead_id))
    assert row["transport_lead_id"] == str(lead_id)
    assert row["extensions"]["transport_lead_id"] == str(lead_id)


@pytest.mark.anyio
async def test_recruitment_application_comments_roundtrip(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        oc_row = await db.execute(
            select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()).limit(1)
        )
        own_company_id = oc_row.scalar_one_or_none()
        if own_company_id is None:
            own_company_id = str(uuid.uuid4())
            db.add(
                OwnCompany(
                    id=own_company_id,
                    tenant_id=tenant_id,
                    name="Test OC",
                )
            )
            await db.commit()
        lead_id = str(uuid.uuid4())
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=str(own_company_id),
                company_id=str(company_id),
                source="website",
                status="new",
                lead_type="candidate",
                payload={"name": "Notes Lead"},
            )
        )
        await db.commit()

    resp = await client.post(
        f"/api/v1/recruitment/applications/{lead_id}/comments",
        headers=manager_headers,
        json={"note": "Перезвонить завтра"},
    )
    assert resp.status_code == 200, resp.text
    comments = resp.json().get("extensions", {}).get("application_comments_v1") or []
    assert len(comments) == 1
    assert comments[0]["text"] == "Перезвонить завтра"


async def _ensure_own_company(db, tenant_id: str) -> str:
    oc_row = await db.execute(
        select(OwnCompany.id).where(OwnCompany.tenant_id == tenant_id).order_by(OwnCompany.created_at.asc()).limit(1)
    )
    own_company_id = oc_row.scalar_one_or_none()
    if own_company_id is not None:
        return str(own_company_id)
    own_company_id = str(uuid.uuid4())
    db.add(OwnCompany(id=own_company_id, tenant_id=tenant_id, name="Test OC"))
    await db.commit()
    return own_company_id


@pytest.mark.anyio
async def test_list_recruitment_applications_filters_by_call_result_and_lifecycle(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        own_company_id = await _ensure_own_company(db, tenant_id)
        fresh_id = str(uuid.uuid4())
        called_id = str(uuid.uuid4())
        db.add(
            Lead(
                id=fresh_id,
                tenant_id=tenant_id,
                own_company_id=str(own_company_id),
                company_id=str(company_id),
                source="meta",
                status="new",
                stage="new",
                lead_type="candidate",
                payload={},
                normalized={
                    "full_name": "Fresh Candidate",
                    "phone": "+48500111000",
                    "intake_resolution_v1": {"status": "new"},
                },
            )
        )
        db.add(
            Lead(
                id=called_id,
                tenant_id=tenant_id,
                own_company_id=str(own_company_id),
                company_id=str(company_id),
                source="meta",
                status="new",
                stage="new",
                lead_type="candidate",
                payload={},
                normalized={
                    "full_name": "Called Candidate",
                    "phone": "+48500111001",
                    "intake_resolution_v1": {"status": "in_progress"},
                    "call_result_v1": {
                        "result": "no_answer",
                        "note": "Try after 18:00",
                        "at": "2026-09-02T10:00:00Z",
                    },
                },
            )
        )
        await db.commit()

    new_resp = await client.get(
        "/api/v1/recruitment/applications",
        headers=manager_headers,
        params={"tab": "new", "limit": 200},
    )
    assert new_resp.status_code == 200, new_resp.text
    new_ids = {item["id"] for item in new_resp.json().get("items", [])}
    assert fresh_id in new_ids
    assert called_id not in new_ids

    progress_resp = await client.get(
        "/api/v1/recruitment/applications",
        headers=manager_headers,
        params={"tab": "in_progress", "limit": 200},
    )
    assert progress_resp.status_code == 200, progress_resp.text
    progress_items = progress_resp.json().get("items", [])
    progress_ids = {item["id"] for item in progress_items}
    assert called_id in progress_ids
    assert fresh_id not in progress_ids
    called_row = next(item for item in progress_items if item["id"] == called_id)
    assert called_row["status"] == "in_progress"
    assert called_row["extensions"]["call_result_v1"]["result"] == "no_answer"
    assert called_row["extensions"]["call_result_v1"]["note"] == "Try after 18:00"

    filtered = await client.get(
        "/api/v1/recruitment/applications",
        headers=manager_headers,
        params={"tab": "all", "call_result": "no_answer", "limit": 200},
    )
    assert filtered.status_code == 200, filtered.text
    filtered_ids = {item["id"] for item in filtered.json().get("items", [])}
    assert called_id in filtered_ids
    assert fresh_id not in filtered_ids

    search = await client.get(
        "/api/v1/recruitment/applications",
        headers=manager_headers,
        params={"tab": "all", "q": "Called Candidate", "limit": 200},
    )
    assert search.status_code == 200, search.text
    search_ids = {item["id"] for item in search.json().get("items", [])}
    assert called_id in search_ids
    assert fresh_id not in search_ids


@pytest.mark.anyio
async def test_recruitment_application_call_result_persists_and_lists(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    async with async_session_maker() as db:
        company_id = await _ensure_company(db, tenant_id)
        own_company_id = await _ensure_own_company(db, tenant_id)
        lead_id = str(uuid.uuid4())
        db.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=str(own_company_id),
                company_id=str(company_id),
                source="meta",
                status="new",
                stage="new",
                lead_type="candidate",
                payload={},
                normalized={
                    "full_name": "Jan Nowak",
                    "phone": "+48500999000",
                    "intake_resolution_v1": {"status": "new"},
                },
            )
        )
        await db.commit()

    note = "Oddzwonić po 18:00, pyta o stawkę"
    saved = await client.post(
        f"/api/v1/recruitment/applications/{lead_id}/call-result",
        headers=manager_headers,
        json={"result": "callback_requested", "note": note},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["status"] == "in_progress"
    assert body["extensions"]["call_result_v1"]["result"] == "callback_requested"
    assert body["extensions"]["call_result_v1"]["note"] == note

    listed = await client.get(
        "/api/v1/recruitment/applications",
        headers=manager_headers,
        params={"tab": "in_progress", "call_result": "callback_requested", "limit": 200},
    )
    assert listed.status_code == 200, listed.text
    items = listed.json().get("items", [])
    row = next((item for item in items if item["id"] == lead_id), None)
    assert row is not None
    assert row["status"] == "in_progress"
    assert row["extensions"]["call_result_v1"]["note"] == note
