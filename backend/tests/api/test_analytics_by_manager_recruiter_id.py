"""G-6 Stage 2c — ``/analytics/by-manager`` surfaces ``recruiter_id``.

Spec: ``docs/specs/operations-loop.md`` §G-6 Stage 2c (ManagerLoadPanel).

The Work Hub ``ManagerLoadPanel`` drills into ``/app/candidates?recruiter_id=<uuid>``,
so the backend aggregate needs to carry the canonical ``users.id`` alongside
the legacy ``manager`` display label. Before this stage the response shape
was ``{manager, total, by_stage, hired}`` — no stable id, FE had no way to
build a deterministic drill-down URL without a second lookup.

Guarantees verified here:

* ``recruiter_id`` key is present on every item (even legacy rows with
  ``Candidate.manager`` free-text only — value is ``null`` in that case,
  so FE can fall back to the ``?manager=<label>`` drill-down path).
* When ``Candidate.recruiter_id`` points to a real user, the aggregate
  item carries that user's UUID string.

Not covered here (deliberately out of scope):
* Stage-view filtering semantics — already locked in by upstream helpers;
  changing the payload is strictly additive.
* Multi-tenancy — default ``manager_headers`` suffice since the endpoint
  scopes by the caller's tenant.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.anyio


async def test_by_manager_items_expose_recruiter_id(client, manager_headers):
    """Every item in ``/analytics/by-manager`` MUST carry a ``recruiter_id`` key.

    Guarantees the FE can always read the field without ``KeyError`` — the
    value is ``None`` for legacy rows without a FK, a UUID string otherwise.
    """
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "ByManagerFK", "last_name": "Probe"},
    )
    assert create_resp.status_code == 200, create_resp.text

    resp = await client.get("/api/v1/analytics/by-manager", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    items = body.get("items")
    assert isinstance(items, list), body

    # At least one item should be returned (the candidate we just created
    # lands on the admin seat by default). Each item has the full shape.
    assert items, body
    for item in items:
        assert "manager" in item, item
        assert "recruiter_id" in item, item
        assert "total" in item, item
        assert "by_stage" in item, item
        assert "hired" in item, item

        rid = item["recruiter_id"]
        assert rid is None or isinstance(rid, str), item
        if isinstance(rid, str):
            # Must look like a UUID string (8-4-4-4-12 hex).
            assert len(rid) == 36 and rid.count("-") == 4, item


async def test_by_manager_items_recruiter_id_matches_assigned_user(
    client, manager_headers
):
    """After assigning a candidate to the admin user (via ``recruiter_id``
    PATCH), the corresponding row MUST expose that user's UUID.

    Guards the Stage F shadow-write contract: the canonical ``recruiter_id``
    column is what drives the aggregate, not the legacy ``manager`` string.
    """
    me_resp = await client.get("/api/v1/users/me", headers=manager_headers)
    assert me_resp.status_code == 200, me_resp.text
    profile = me_resp.json().get("profile") or {}
    my_user_id = profile.get("user_id")
    assert my_user_id, me_resp.text

    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "ByManagerOwner", "last_name": "Probe"},
    )
    assert create_resp.status_code == 200, create_resp.text
    cid = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"recruiter_id": my_user_id},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    resp = await client.get("/api/v1/analytics/by-manager", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json().get("items") or []
    matching = [it for it in items if it.get("recruiter_id") == my_user_id]
    # Admin/recruiter auto-assignment + explicit PATCH together guarantee at
    # least one row keyed by our UUID; multiple rows are fine (other probes
    # from earlier tests), so we only assert non-empty.
    assert matching, items
