"""Risk-band automation helpers (Phase D)."""

from __future__ import annotations

import pytest

from backend.app.services.automation_rules import RISK_BAND_ORDER, risk_band_at_least


def test_risk_band_at_least_ordering() -> None:
    assert risk_band_at_least("high", "high")
    assert risk_band_at_least("critical", "high")
    assert not risk_band_at_least("medium", "high")
    assert not risk_band_at_least("low", "high")
    assert risk_band_at_least("critical", "critical")
    assert not risk_band_at_least("high", "critical")


def test_risk_band_order_complete() -> None:
    assert RISK_BAND_ORDER["low"] < RISK_BAND_ORDER["critical"]
