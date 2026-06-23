"""Track B — dashboard KPI projection tests."""

from __future__ import annotations

from backend.app.document_runtime.dashboard_projection import (
    aggregate_runtime_items_to_kpis,
    build_dashboard_kpi_payload,
    extract_runtime_items_from_hub_section,
)


def test_extract_runtime_items_from_hub_section() -> None:
    hub = {
        "applied": True,
        "document_runtime": {
            "items": [
                {"document_type_code": "passport", "document_runtime": {"workflow_status": "missing"}},
                {"document_type_code": "visa", "document_runtime": {"expiry_status": "expired"}},
            ],
        },
    }
    items = extract_runtime_items_from_hub_section(hub)
    assert len(items) == 2


def test_aggregate_runtime_items_to_kpis() -> None:
    items = [
        {"document_runtime": {"expiry_status": "expired"}},
        {"document_runtime": {"expiry_status": "expiring_soon", "days_left": 5}},
        {"document_runtime": {"expiry_status": "expiring_soon", "days_left": 14}},
        {"document_runtime": {"runtime_signal": "pending_verification"}},
        {"document_runtime": {"workflow_status": "missing"}},
        {"document_runtime": {"satisfies_requirement": True}},
    ]
    kpis = aggregate_runtime_items_to_kpis(items)
    assert kpis["expired"] == 1
    assert kpis["expiring_soon"] == 2
    assert kpis["expiring_7d"] == 1
    assert kpis["pending_review"] == 1
    assert kpis["missing_required"] == 1
    assert kpis["ready_documents"] == 1


def test_build_dashboard_kpi_payload_shape() -> None:
    payload = build_dashboard_kpi_payload(
        kpis={"expired": 2},
        candidates_scanned=10,
        runtime_candidates=8,
        runtime_items_scanned=24,
        source="runtime",
        period={"from": None, "to": None},
    )
    assert payload["evaluation_version"] == "document_runtime_dashboard_kpis_v1"
    assert payload["source"] == "runtime"
    assert payload["kpis"]["expired"] == 2
    assert payload["kpis"]["missing_required"] == 0
