from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.app.services import tenant_quota
from backend.app.services.tenant_limits import TenantLimits


@pytest.mark.asyncio
async def test_ensure_active_records_quota_allows_when_under_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    limits = TenantLimits(
        plan="team",
        max_recruiters=0,
        max_supervisors=0,
        max_client_managers=0,
        max_viewers=0,
        max_storage_gb=0,
        max_companies=0,
        max_candidates_active=10,
        max_vacancies_active=0,
        max_documents=0,
        max_public_portal_links=0,
    )
    monkeypatch.setattr(tenant_quota, "get_tenant_limits", AsyncMock(return_value=limits))
    monkeypatch.setattr(
        tenant_quota,
        "count_active_records",
        AsyncMock(return_value={"leads": 2, "candidates": 3, "clients": 4, "total": 9}),
    )

    await tenant_quota.ensure_active_records_quota(None, "t1")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_ensure_active_records_quota_raises_with_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    limits = TenantLimits(
        plan="starter",
        max_recruiters=0,
        max_supervisors=0,
        max_client_managers=0,
        max_viewers=0,
        max_storage_gb=0,
        max_companies=0,
        max_candidates_active=5,
        max_vacancies_active=0,
        max_documents=0,
        max_public_portal_links=0,
    )
    monkeypatch.setattr(tenant_quota, "get_tenant_limits", AsyncMock(return_value=limits))
    monkeypatch.setattr(
        tenant_quota,
        "count_active_records",
        AsyncMock(return_value={"leads": 1, "candidates": 2, "clients": 2, "total": 5}),
    )

    with pytest.raises(HTTPException) as ei:
        await tenant_quota.ensure_active_records_quota(None, "t1")  # type: ignore[arg-type]

    err = ei.value
    assert err.status_code == 402
    assert isinstance(err.detail, dict)
    assert err.detail.get("code") == "active_records_limit_reached"
    assert err.detail.get("breakdown") == {"leads": 1, "candidates": 2, "clients": 2}
