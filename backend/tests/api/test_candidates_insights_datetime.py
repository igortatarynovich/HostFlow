"""Regression: candidate insights must compare naive UTC timestamps safely."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.api.v1.candidates import repo as cand_repo


def test_coerce_naive_utc_datetime_from_naive() -> None:
    naive = datetime(2026, 7, 14, 12, 0, 0)
    out = cand_repo._coerce_naive_utc_datetime(naive)
    assert out == naive
    assert out is not None and out.tzinfo is None


def test_coerce_naive_utc_datetime_from_aware() -> None:
    aware = datetime(2026, 7, 14, 14, 0, 0, tzinfo=timezone.utc)
    out = cand_repo._coerce_naive_utc_datetime(aware)
    assert out == datetime(2026, 7, 14, 14, 0, 0)
    assert out is not None and out.tzinfo is None
