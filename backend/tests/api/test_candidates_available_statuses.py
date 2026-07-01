"""Smoke tests for ``GET /api/v1/candidates/available-statuses``.

The endpoint returns distinct ``Candidate.stage`` / ``Candidate.status`` values
for the same tenant scope and ACL as the main candidates list (without applying
list-only filters), so the UI can offer filter options grounded in real data.
"""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_candidates_available_statuses_smoke(client, manager_headers) -> None:
    response = await client.get(
        "/api/v1/candidates/available-statuses",
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("schema_version") == 1
    assert isinstance(data.get("stages"), list)
    assert isinstance(data.get("statuses"), list)
    assert isinstance(data.get("vacancy_ids"), list)
    assert isinstance(data.get("assignee_ids"), list)
