from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from backend.app.db.session import async_session_maker
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus


@pytest.mark.anyio
async def test_candidates_include_document_summary_fields(
    client,
    manager_headers,
    tenant_id: str,
    candidate_id: str,
) -> None:
    async with async_session_maker() as session:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )
        ordered_at = date.today()
        valid_from = ordered_at + timedelta(days=10)
        document = Document(
            id=str(uuid4()),
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            doc_type="work_permit",
            status=DocumentStatus.requested,
            ordered_at=ordered_at,
            valid_from=valid_from,
            files=[{"name": "permit.pdf"}],
        )
        session.add(document)
        await session.commit()

    response = await client.get("/api/v1/candidates", headers=manager_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    items = payload.get("items", [])
    target = next((item for item in items if item["id"] == candidate_id), None)
    assert target is not None, "candidate with documents should be returned"
    assert target["docs_readiness_state"] in {"ordered", "requested"}
    assert target["docs_has_files"] is True
    assert target["docs_last_ordered_at"].startswith(ordered_at.isoformat())
    assert target["docs_next_valid_from"].startswith(valid_from.isoformat())

    ordered_only = await client.get(
        "/api/v1/candidates",
        headers=manager_headers,
        params={"documents_ordered": "ordered"},
    )
    assert ordered_only.status_code == 200
    ordered_items = ordered_only.json().get("items", [])
    assert any(item["id"] == candidate_id for item in ordered_items)

    not_ordered = await client.get(
        "/api/v1/candidates",
        headers=manager_headers,
        params={"documents_ordered": "not_ordered"},
    )
    assert not_ordered.status_code == 200
    not_ordered_items = not_ordered.json().get("items", [])
    assert all(item["id"] != candidate_id for item in not_ordered_items)
