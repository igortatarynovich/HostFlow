"""Track B — dashboard KPI predicate tests."""

from __future__ import annotations

from backend.app.document_runtime.kpi_predicates import (
    DOCUMENT_RUNTIME_DASHBOARD_KPIS,
    increment_dashboard_kpis,
    runtime_matches_dashboard_kpi,
)


def test_expired_kpi() -> None:
    assert runtime_matches_dashboard_kpi({"expiry_status": "expired"}, "expired") is True
    assert runtime_matches_dashboard_kpi({"expiry_status": "valid"}, "expired") is False


def test_expiring_7d_uses_days_left_metadata() -> None:
    assert runtime_matches_dashboard_kpi(
        {"expiry_status": "expiring_soon", "days_left": 7},
        "expiring_7d",
    ) is True
    assert runtime_matches_dashboard_kpi(
        {"expiry_status": "expiring_soon", "days_left": 8},
        "expiring_7d",
    ) is False
    assert runtime_matches_dashboard_kpi({"expiry_status": "expiring_soon"}, "expiring_7d") is False


def test_pending_and_missing_kpis() -> None:
    assert runtime_matches_dashboard_kpi({"runtime_signal": "pending_verification"}, "pending_review") is True
    assert runtime_matches_dashboard_kpi({"workflow_status": "missing"}, "missing_required") is True


def test_increment_dashboard_kpis() -> None:
    counts = {key: 0 for key in DOCUMENT_RUNTIME_DASHBOARD_KPIS}
    increment_dashboard_kpis(counts, {"workflow_status": "missing", "expiry_status": "expired"})
    assert counts["missing_required"] == 1
    assert counts["expired"] == 1
