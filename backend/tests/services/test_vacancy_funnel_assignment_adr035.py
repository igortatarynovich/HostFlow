"""ADR-035 §12: Vacancy.funnel_id is assignment SoT; profile is legacy fallback."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.services.recruitment_funnel_assignment import resolve_funnel_id_for_vacancy


@pytest.mark.asyncio
async def test_resolve_funnel_id_prefers_vacancy_over_profile() -> None:
    vacancy = SimpleNamespace(
        funnel_id="vac-funnel-1",
        candidate_profile_id="profile-1",
    )
    db = MagicMock()
    db.execute = AsyncMock()

    result = await resolve_funnel_id_for_vacancy(
        db, tenant_id="tenant-1", vacancy=vacancy  # type: ignore[arg-type]
    )
    assert result == "vac-funnel-1"
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_funnel_id_falls_back_to_legacy_profile() -> None:
    vacancy = SimpleNamespace(
        funnel_id=None,
        candidate_profile_id="profile-1",
    )
    profile = SimpleNamespace(funnel_id="profile-funnel-9")

    result_proxy = MagicMock()
    result_proxy.scalar_one_or_none.return_value = profile
    db = MagicMock()
    db.execute = AsyncMock(return_value=result_proxy)

    result = await resolve_funnel_id_for_vacancy(
        db, tenant_id="tenant-1", vacancy=vacancy  # type: ignore[arg-type]
    )
    assert result == "profile-funnel-9"
    db.execute.assert_awaited()
