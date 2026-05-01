"""GET /communications/planner/events/{id} — calendar deep-link (G-6)."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.anyio


async def test_get_planner_event_404_unknown_id(client, manager_headers):
    import uuid

    rid = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/communications/planner/events/{rid}", headers=manager_headers)
    assert resp.status_code == 404, resp.text
