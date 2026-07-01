from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.app.services import plan_feature_gates


@pytest.mark.asyncio
async def test_ensure_lead_source_limit_allows_within_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plan_feature_gates, "resolve_plan_bucket_for_limits", AsyncMock(return_value="team"))

    await plan_feature_gates.ensure_lead_source_limit(
        None,  # type: ignore[arg-type]
        "tenant-1",
        current_count=2,
        extra_sources=1,
    )


@pytest.mark.asyncio
async def test_ensure_lead_source_limit_blocks_over_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plan_feature_gates, "resolve_plan_bucket_for_limits", AsyncMock(return_value="starter"))

    with pytest.raises(HTTPException) as ei:
        await plan_feature_gates.ensure_lead_source_limit(
            None,  # type: ignore[arg-type]
            "tenant-1",
            current_count=1,
            extra_sources=1,
        )

    err = ei.value
    assert err.status_code == 402
    assert isinstance(err.detail, dict)
    assert err.detail.get("code") == "lead_sources_limit_reached"
