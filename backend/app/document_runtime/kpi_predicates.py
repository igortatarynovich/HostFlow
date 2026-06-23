"""Dashboard KPI predicates over document_runtime_v1 (Track B — shared with Track A)."""

from __future__ import annotations

from typing import Any

DOCUMENT_RUNTIME_DASHBOARD_KPIS = (
    "expired",
    "expiring_soon",
    "expiring_7d",
    "pending_review",
    "rejected",
    "missing_required",
    "ready_documents",
)

DashboardKpiKey = str


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def runtime_matches_dashboard_kpi(runtime: dict[str, Any] | None, kpi: str) -> bool:
    """Return True when a required checklist runtime item matches dashboard KPI vocabulary v1."""
    if not runtime or not isinstance(runtime, dict):
        return False

    workflow = _norm(runtime.get("workflow_status"))
    expiry = _norm(runtime.get("expiry_status"))
    signal = _norm(runtime.get("runtime_signal"))
    days_left = runtime.get("days_left")

    key = _norm(kpi)
    if key == "expired":
        return expiry == "expired"
    if key == "expiring_soon":
        return expiry == "expiring_soon"
    if key == "expiring_7d":
        if expiry != "expiring_soon":
            return False
        if days_left is None:
            return False
        try:
            return int(days_left) <= 7
        except (TypeError, ValueError):
            return False
    if key == "pending_review":
        return signal == "pending_verification"
    if key == "rejected":
        return workflow == "rejected"
    if key == "missing_required":
        return workflow == "missing"
    if key == "ready_documents":
        return runtime.get("satisfies_requirement") is True
    return False


def empty_dashboard_kpi_counts() -> dict[str, int]:
    return {key: 0 for key in DOCUMENT_RUNTIME_DASHBOARD_KPIS}


def increment_dashboard_kpis(counts: dict[str, int], runtime: dict[str, Any] | None) -> None:
    for key in DOCUMENT_RUNTIME_DASHBOARD_KPIS:
        if runtime_matches_dashboard_kpi(runtime, key):
            counts[key] = int(counts.get(key, 0)) + 1
