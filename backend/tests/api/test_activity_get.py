"""GET /activities/{id} — single activity for calendar deep-link (G-6)."""

from __future__ import annotations

import uuid

import pytest


pytestmark = pytest.mark.anyio


async def test_get_activity_404_unknown_id(client, manager_headers):
    rid = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/activities/{rid}", headers=manager_headers)
    assert resp.status_code == 404, resp.text
