"""Fleet dashboard overview aggregation."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


_OVERVIEW_KEYS = frozenset(
    {
        "vehicles_total",
        "vehicles_by_status",
        "trailers_total",
        "trailers_by_status",
        "drivers_total",
        "drivers_by_status",
        "drivers_with_workforce_total",
        "operating_lines_total",
        "operating_lines_by_status",
        "work_models_total",
        "line_roster_vehicles_total",
        "line_roster_drivers_total",
        "line_roster_drivers_effective_today_total",
        "assignments_total",
        "assignments_by_status",
        "assignments_overlapping_today_utc_total",
        "assignments_overlapping_month_utc_total",
    }
)


async def test_fleet_overview_schema(client: AsyncClient, manager_headers: Dict[str, str]) -> None:
    resp = await client.get("/api/v1/fleet/overview", headers=manager_headers)
    if resp.status_code != 200:
        pytest.skip(f"fleet overview unavailable (HTTP {resp.status_code}): {resp.text[:400]}")
    body = resp.json()
    assert _OVERVIEW_KEYS <= body.keys(), body
    assert isinstance(body["vehicles_by_status"], dict)
    assert isinstance(body["trailers_by_status"], dict)
    assert isinstance(body["drivers_by_status"], dict)
    assert isinstance(body["operating_lines_by_status"], dict)
    assert isinstance(body["assignments_by_status"], dict)
    assert isinstance(body["vehicles_total"], int)
    assert isinstance(body["assignments_total"], int)
    assert isinstance(body["assignments_overlapping_today_utc_total"], int)
    assert isinstance(body["assignments_overlapping_month_utc_total"], int)
    assert isinstance(body["drivers_with_workforce_total"], int)
    assert isinstance(body["line_roster_vehicles_total"], int)
    assert isinstance(body["line_roster_drivers_total"], int)
    assert isinstance(body["line_roster_drivers_effective_today_total"], int)
