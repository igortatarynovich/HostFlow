"""Shared helpers for lead-stage RODO gate tests (art.14 before contact / process)."""

from __future__ import annotations

from httpx import AsyncClient


async def satisfy_lead_rodo_via_source_for_tests(client: AsyncClient, manager_headers: dict, lead_id: str) -> None:
    """Mark ``normalized['rodo'].status = source_provided`` (no SMTP) so POST .../process is allowed."""
    resp = await client.post(
        f"/api/v1/leads/{lead_id}/compliance/rodo/source-provided",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
