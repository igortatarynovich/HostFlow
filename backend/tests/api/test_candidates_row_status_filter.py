"""``GET /api/v1/candidates`` — ``Candidate.status`` (row state) vs ``Candidate.stage`` (funnel).

Legacy behaviour treated ``?status=`` as a funnel stage alias. Row status is now filtered
only via ``Candidate.status``; ``?stage=`` / ``?stages=`` continue to map to ``Candidate.stage``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.db.session import async_session_maker


@pytest.mark.anyio
async def test_candidates_statuses_filters_row_status_not_stage(
    client,
    manager_headers,
    tenant_id: str,
    bootstrap: dict[str, str],
) -> None:
    cid = bootstrap["candidate_id"]
    try:
        async with async_session_maker() as session:
            await session.execute(
                text(
                    """
                    UPDATE candidates
                    SET stage = :stage, status = :row_status, updated_at = updated_at
                    WHERE id = :id AND tenant_id = :tenant_id
                    """
                ),
                {
                    "id": cid,
                    "tenant_id": tenant_id,
                    "stage": "new",
                    "row_status": "returned_for_revision",
                },
            )
            await session.commit()

        facets = await client.get("/api/v1/candidates/available-statuses", headers=manager_headers)
        assert facets.status_code == 200, facets.text
        facet_statuses = facets.json().get("statuses") or []
        assert "returned_for_revision" in facet_statuses

        by_row = await client.get(
            "/api/v1/candidates",
            headers=manager_headers,
            params={"statuses": "returned_for_revision", "limit": 50, "offset": 0},
        )
        assert by_row.status_code == 200, by_row.text
        ids = [item["id"] for item in by_row.json().get("items", [])]
        assert cid in ids

        wrong_stage = await client.get(
            "/api/v1/candidates",
            headers=manager_headers,
            params={"stages": "returned_for_revision", "limit": 50, "offset": 0},
        )
        assert wrong_stage.status_code == 200
        ids_wrong = [item["id"] for item in wrong_stage.json().get("items", [])]
        assert cid not in ids_wrong

        async with async_session_maker() as session:
            await session.execute(
                text(
                    """
                    UPDATE candidates
                    SET stage = :stage, status = :row_status, updated_at = updated_at
                    WHERE id = :id AND tenant_id = :tenant_id
                    """
                ),
                {
                    "id": cid,
                    "tenant_id": tenant_id,
                    "stage": "docs_wait",
                    "row_status": "handed_off",
                },
            )
            await session.commit()

        facets2 = await client.get("/api/v1/candidates/available-statuses", headers=manager_headers)
        assert facets2.status_code == 200
        assert "handed_off" in (facets2.json().get("statuses") or [])

        by_handed_off = await client.get(
            "/api/v1/candidates",
            headers=manager_headers,
            params={"status": "handed_off", "limit": 50, "offset": 0},
        )
        assert by_handed_off.status_code == 200
        assert cid in [item["id"] for item in by_handed_off.json().get("items", [])]

        and_both = await client.get(
            "/api/v1/candidates",
            headers=manager_headers,
            params={"stages": "docs_wait", "statuses": "handed_off", "limit": 50, "offset": 0},
        )
        assert and_both.status_code == 200
        assert cid in [item["id"] for item in and_both.json().get("items", [])]

        and_miss = await client.get(
            "/api/v1/candidates",
            headers=manager_headers,
            params={"stages": "employed", "statuses": "handed_off", "limit": 50, "offset": 0},
        )
        assert and_miss.status_code == 200
        assert cid not in [item["id"] for item in and_miss.json().get("items", [])]

        list_row = await client.get(
            "/api/v1/candidates",
            headers=manager_headers,
            params={"statuses": "handed_off", "limit": 100, "offset": 0, "compact": True},
        )
        assert list_row.status_code == 200
        sample = next((i for i in list_row.json().get("items", []) if i.get("id") == cid), None)
        assert sample is not None
        assert sample.get("row_status") == "handed_off"
        assert sample.get("stage") == "docs_wait"

    finally:
        async with async_session_maker() as session:
            await session.execute(
                text(
                    """
                    UPDATE candidates
                    SET stage = NULL, status = NULL, updated_at = updated_at
                    WHERE id = :id AND tenant_id = :tenant_id
                    """
                ),
                {"id": cid, "tenant_id": tenant_id},
            )
            await session.commit()
