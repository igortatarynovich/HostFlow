"""G-6 Stage 2e — ``GET /users/me`` exposes ``is_solo_admin``.

Used by the Work Hub to pick ``admin_solo`` vs ``admin_team`` profile
(`hostflow-frontend/src/modules/workHub/useWorkHubProfile.ts`).

Contract:
  ``is_solo_admin`` is ``True`` iff the caller's role is owner-class
  (``administrator`` or ``superadmin``) **and** the tenant has exactly one
  active, non-deleted member (see ``users_service._count_active_tenant_members``).
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.anyio


async def test_users_me_includes_is_solo_admin_boolean(client, manager_headers):
    resp = await client.get("/api/v1/users/me", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "is_solo_admin" in body
    assert isinstance(body["is_solo_admin"], bool)
