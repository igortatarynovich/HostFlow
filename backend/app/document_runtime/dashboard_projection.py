"""Track B — aggregate document_runtime_v1 checklist items into dashboard KPI counts."""

from __future__ import annotations

from typing import Any

from backend.app.document_runtime.kpi_predicates import (
    DOCUMENT_RUNTIME_DASHBOARD_KPIS,
    empty_dashboard_kpi_counts,
    increment_dashboard_kpis,
)


def extract_runtime_items_from_hub_section(hub_section: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not hub_section or not isinstance(hub_section, dict):
        return []
    runtime_section = hub_section.get("document_runtime")
    if isinstance(runtime_section, dict):
        items = runtime_section.get("items")
        if isinstance(items, list):
            return [row for row in items if isinstance(row, dict)]
    return []


def aggregate_runtime_items_to_kpis(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = empty_dashboard_kpi_counts()
    for row in items or []:
        runtime = row.get("document_runtime")
        if isinstance(runtime, dict):
            increment_dashboard_kpis(counts, runtime)
    return counts


def build_dashboard_kpi_payload(
    *,
    kpis: dict[str, int],
    candidates_scanned: int,
    runtime_candidates: int,
    runtime_items_scanned: int,
    source: str,
    period: dict[str, Any],
) -> dict[str, Any]:
    return {
        "evaluation_version": "document_runtime_dashboard_kpis_v1",
        "source": source,
        "kpis": {key: int(kpis.get(key, 0)) for key in DOCUMENT_RUNTIME_DASHBOARD_KPIS},
        "candidates_scanned": candidates_scanned,
        "runtime_candidates": runtime_candidates,
        "runtime_items_scanned": runtime_items_scanned,
        "period": period,
    }
