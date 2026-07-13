"""Candidate insights date filters — timezone-safe comparisons."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.app.api.v1.candidates import repo as cand_repo


def test_coerce_naive_utc_datetime_from_naive() -> None:
    naive = datetime(2026, 7, 10, 0, 0, 0)
    coerced = cand_repo._coerce_naive_utc_datetime(naive)
    assert coerced == naive
    assert coerced is not None and coerced.tzinfo is None


def test_coerce_naive_utc_datetime_from_aware() -> None:
    aware = datetime(2026, 7, 10, 15, 30, 0, tzinfo=timezone.utc)
    coerced = cand_repo._coerce_naive_utc_datetime(aware)
    assert coerced == datetime(2026, 7, 10, 15, 30, 0)
    assert coerced is not None and coerced.tzinfo is None


@pytest.mark.anyio
async def test_count_candidates_insights_accepts_naive_created_range(
    tenant_id: str,
) -> None:
    from backend.app.db.session import async_session_maker

    filters = {
        "dt_from": datetime.combine(date(2020, 1, 1), datetime.min.time()),
        "dt_to": datetime.combine(date(2030, 12, 31), datetime.max.time()),
    }
    async with async_session_maker() as db:
        payload = await cand_repo.count_candidates_insights(db, tenant_id=tenant_id, filters=filters)
    assert isinstance(payload, dict)
    assert "total" in payload
