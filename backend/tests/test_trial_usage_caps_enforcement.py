from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.app.services import plan_feature_gates


@pytest.mark.asyncio
async def test_enforce_trial_usage_cap_and_increment_noop_for_unknown_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    trial_active = AsyncMock(return_value=True)
    monkeypatch.setattr(plan_feature_gates, "_tenant_trial_active", trial_active)

    await plan_feature_gates.enforce_trial_usage_cap_and_increment(
        None,  # type: ignore[arg-type]
        tenant_id="t1",
        metric="unknown_metric",
        increment=1,
    )
    trial_active.assert_not_called()


@pytest.mark.asyncio
async def test_enforce_trial_usage_cap_and_increment_calls_usage_services(monkeypatch: pytest.MonkeyPatch) -> None:
    trial_active = AsyncMock(return_value=True)
    monkeypatch.setattr(plan_feature_gates, "_tenant_trial_active", trial_active)

    ensure_mock = AsyncMock()
    increment_mock = AsyncMock()

    import backend.app.services.tenant_limits as tenant_limits

    monkeypatch.setattr(tenant_limits, "ensure_usage_limit_not_exceeded", ensure_mock)
    monkeypatch.setattr(tenant_limits, "increment_tenant_usage", increment_mock)

    await plan_feature_gates.enforce_trial_usage_cap_and_increment(
        None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        metric=plan_feature_gates.TRIAL_AUTOMATION_RUNS_METRIC,
        increment=1,
    )

    trial_active.assert_awaited_once()
    ensure_mock.assert_awaited_once()
    increment_mock.assert_awaited_once()
