"""GET /settings/billing/quota-headroom — tenant members (not only billing roles)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

BILLING_BASE = "/api/v1/settings/billing"


@pytest.mark.anyio
async def test_quota_headroom_recruiter_ok(client: AsyncClient, recruiter_headers: dict) -> None:
    resp = await client.get(f"{BILLING_BASE}/quota-headroom", headers=recruiter_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "leads_created_this_month",
        "max_leads_created_per_month",
        "candidates_active_count",
        "max_candidates_active",
        "storage_used_gb",
        "max_storage_gb",
    ):
        assert key in body


@pytest.mark.anyio
async def test_quota_headroom_viewer_ok(client: AsyncClient, viewer_headers: dict) -> None:
    resp = await client.get(f"{BILLING_BASE}/quota-headroom", headers=viewer_headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_billing_summary_recruiter_forbidden(client: AsyncClient, recruiter_headers: dict) -> None:
    resp = await client.get(f"{BILLING_BASE}/summary", headers=recruiter_headers)
    assert resp.status_code == 403, resp.text
