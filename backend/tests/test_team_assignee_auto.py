from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.team_assignee_auto import (
    merge_assignee_resolution,
    pick_first_available_manager_excluding,
    planner_event_load_weight,
    reminder_load_weight,
    resolve_assignee_id_with_queue_fallback,
    smart_assignee_load_context,
)
from backend.app.services.plan_feature_gates import plan_allows_smart_operations_bundle
from fastapi import HTTPException


def test_pick_first_respects_order_and_excludes() -> None:
    items = [
        {"managerId": "a", "enabled": True, "availability": {"state": "meeting"}},
        {"managerId": "b", "enabled": True, "availability": {"state": "available"}},
        {"managerId": "c", "enabled": True, "availability": {"state": "available"}},
    ]
    p = pick_first_available_manager_excluding(items, exclude_id="x")
    assert p and p.get("managerId") == "b"
    p2 = pick_first_available_manager_excluding(items, exclude_id="b")
    assert p2 and p2.get("managerId") == "c"


def test_merge_assignee_resolution() -> None:
    m = merge_assignee_resolution({"a": 1}, {"assignee_auto_reassigned": True, "resolved_assignee_id": "b"})
    assert m.get("assignee_resolution", {}).get("resolved_assignee_id") == "b"
    m2 = merge_assignee_resolution({"a": 1}, None)
    assert "assignee_resolution" not in m2


@pytest.mark.anyio
async def test_resolve_falls_back_when_request_offline() -> None:
    tenant = SimpleNamespace(
        settings={
            "communications": {
                "managerQueue": {
                    "respectAvailability": True,
                    "items": [
                        {"managerId": "u1", "enabled": True, "availability": {"state": "offline"}},
                        {"managerId": "u2", "enabled": True, "availability": {"state": "available"}},
                    ],
                }
            }
        }
    )

    class Sess:
        async def get(self, *a, **k):
            return tenant

    db = Sess()
    eff, audit = await resolve_assignee_id_with_queue_fallback(
        db, tenant_id="t1", assignee_id="u1", allow_unavailable_assignee=False
    )
    assert eff == "u2"
    assert audit and audit.get("resolved_assignee_id") == "u2"


@pytest.mark.anyio
async def test_resolve_raises_when_no_alternative() -> None:
    tenant = SimpleNamespace(
        settings={
            "communications": {
                "managerQueue": {
                    "respectAvailability": True,
                    "items": [
                        {"managerId": "u1", "enabled": True, "availability": {"state": "offline"}},
                        {"managerId": "u2", "enabled": True, "availability": {"state": "meeting"}},
                    ],
                }
            }
        }
    )

    class Sess:
        async def get(self, *a, **k):
            return tenant

    db = Sess()
    with pytest.raises(HTTPException) as ei:
        await resolve_assignee_id_with_queue_fallback(
            db, tenant_id="t1", assignee_id="u1", allow_unavailable_assignee=False
        )
    assert ei.value.status_code == 422


def test_planner_event_load_weight_not_flat() -> None:
    t = planner_event_load_weight(kind="meeting", priority="normal", status="planned")
    c = planner_event_load_weight(kind="task", priority="normal", status="planned")
    assert t > c


def test_reminder_load_weight_overdue_stronger() -> None:
    a = reminder_load_weight(rtype="custom", priority="normal", status="pending")
    b = reminder_load_weight(rtype="custom", priority="normal", status="overdue")
    assert b > a


def test_smart_operations_same_gate_as_team_tier() -> None:
    assert plan_allows_smart_operations_bundle("team") is True
    assert plan_allows_smart_operations_bundle("starter") is False
    assert plan_allows_smart_operations_bundle("free") is False


@pytest.mark.anyio
async def test_smart_assignee_load_context_gated_by_plan() -> None:
    anchor = datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc)
    with patch(
        "backend.app.services.team_assignee_auto.resolve_tenant_plan_code",
        new=AsyncMock(return_value="starter"),
    ):
        assert (
            await smart_assignee_load_context(AsyncMock(), tenant_id="t1", anchor=anchor)
        ) is None
    with patch(
        "backend.app.services.team_assignee_auto.resolve_tenant_plan_code",
        new=AsyncMock(return_value="team"),
    ):
        out = await smart_assignee_load_context(AsyncMock(), tenant_id="t1", anchor=anchor)
        assert out == {"anchor": anchor}
    assert await smart_assignee_load_context(AsyncMock(), tenant_id="t1", anchor=None) is None


def test_sla_reminder_types_have_explicit_load_weight() -> None:
    """``reminders_v2._SLA_REMINDER_TYPES`` must stay listed in ``assignee_load_taxonomy``."""
    from backend.app.api.v1.reminders_v2 import _SLA_REMINDER_TYPES

    from backend.app.services.assignee_load_taxonomy import REMINDER_TYPE_BASE_WEIGHT

    for t in _SLA_REMINDER_TYPES:
        assert t in REMINDER_TYPE_BASE_WEIGHT, f"missing load row for SLA reminder type {t!r}"


def _make_exec_mock(planner_rows: list, reminder_rows: list) -> type:
    n: dict[str, int] = {"i": 0}

    class _R:
        def __init__(self, rows: list[Any]) -> None:
            self._rows = rows

        def all(self) -> list[Any]:
            return self._rows

    class Sess:
        def __init__(self, t: object) -> None:
            self._t = t

        async def get(self, *a: Any, **k: Any) -> object:
            return self._t

        async def execute(self, *a: Any, **k: Any) -> _R:
            n["i"] += 1
            if n["i"] == 1:
                return _R(planner_rows)
            return _R(reminder_rows)

    return Sess


@pytest.mark.anyio
async def test_resolve_picks_least_weighted_load_with_anchor() -> None:
    """u2 and u3 available: DB has a heavy meeting on u2 that day → pick u3."""
    tenant = SimpleNamespace(
        settings={
            "communications": {
                "managerQueue": {
                    "respectAvailability": True,
                    "items": [
                        {"managerId": "u1", "enabled": True, "availability": {"state": "offline"}},
                        {"managerId": "u2", "enabled": True, "availability": {"state": "available"}},
                        {"managerId": "u3", "enabled": True, "availability": {"state": "available"}},
                    ],
                }
            }
        }
    )
    Sess = _make_exec_mock(
        planner_rows=[("u2", "meeting", "normal", "planned")],
        reminder_rows=[],
    )
    anchor = datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc)
    eff, audit = await resolve_assignee_id_with_queue_fallback(
        Sess(tenant),  # type: ignore[arg-type]
        tenant_id="t1",
        assignee_id="u1",
        allow_unavailable_assignee=False,
        load_context={"anchor": anchor},
    )
    assert eff == "u3"
    assert audit
    assert audit.get("resolved_assignee_id") == "u3"
    assert audit.get("resolution_method") == "least_weighted_load"
    assert "per_manager_load" in audit
