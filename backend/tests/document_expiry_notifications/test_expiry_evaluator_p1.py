"""Document Expiry Notifications P1 — expiry event evaluator tests."""

from __future__ import annotations

from datetime import date, timedelta

from backend.app.document_expiry_notifications.constants import (
    EVENT_DOCUMENT_EXPIRED,
    EVENT_DOCUMENT_EXPIRING_SOON,
    NOTIFICATION_EVENT_V1,
    SOURCE_LAYER,
)
from backend.app.document_expiry_notifications.evaluator import (
    build_expiry_event_key,
    evaluate_document_expiry_events,
    evaluate_expiry_events_from_runtime_delivery,
)
from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.delivery_contract import (
    build_instances_delivery_via_contract,
    enrich_documents_via_contract,
)
from backend.app.document_runtime.evaluator import evaluate_document_runtime


def _snapshot(
    *,
    status: str = "approved",
    expires_on: str | None = None,
    document_id: str = "doc-1",
    doc_type: str = "passport",
    tenant_id: str = "tenant-1",
    owner_id: str = "cand-1",
) -> dict:
    row = {
        "document_id": document_id,
        "type": doc_type,
        "status": status,
        "has_files": True,
        "expires_on": expires_on,
        "tenant_id": tenant_id,
        "owner_type": "candidate",
        "owner_id": owner_id,
    }
    enriched = enrich_documents_via_contract([row])[0]
    return enriched


def _runtime(**kwargs: object) -> dict:
    snap = _snapshot(**kwargs)
    return snap


def test_p1_expired_document_emits_document_expired() -> None:
    past = (date.today() - timedelta(days=3)).isoformat()
    events = evaluate_document_expiry_events([_runtime(expires_on=past)])
    assert len(events) == 1
    event = events[0]
    assert event["evaluation_version"] == NOTIFICATION_EVENT_V1
    assert event["event_code"] == EVENT_DOCUMENT_EXPIRED
    assert event["source_layer"] == SOURCE_LAYER
    assert event["severity"] == "critical"
    assert event["document_runtime"]["expiry_status"] == "expired"


def test_p1_expiring_soon_emits_document_expiring_soon() -> None:
    soon = (date.today() + timedelta(days=10)).isoformat()
    events = evaluate_document_expiry_events([_runtime(expires_on=soon)])
    assert len(events) == 1
    assert events[0]["event_code"] == EVENT_DOCUMENT_EXPIRING_SOON
    assert events[0]["severity"] == "warning"
    assert events[0]["expiring_soon_window_days"] == 30


def test_p1_valid_outside_window_no_event() -> None:
    future = (date.today() + timedelta(days=120)).isoformat()
    events = evaluate_document_expiry_events([_runtime(expires_on=future)])
    assert events == []


def test_p1_no_expiry_no_event() -> None:
    events = evaluate_document_expiry_events([_runtime(expires_on=None)])
    assert events == []


def test_p1_rejected_document_no_expiry_event_even_if_past_date() -> None:
    past = (date.today() - timedelta(days=5)).isoformat()
    events = evaluate_document_expiry_events([_runtime(status="rejected", expires_on=past)])
    assert events == []


def test_p1_deterministic_event_key() -> None:
    past = (date.today() - timedelta(days=1)).isoformat()
    snap = _runtime(expires_on=past, document_id="doc-abc")
    events = evaluate_document_expiry_events([snap, snap])
    assert len(events) == 1
    expected_key = build_expiry_event_key(
        tenant_id="tenant-1",
        owner_type="candidate",
        owner_id="cand-1",
        event_code=EVENT_DOCUMENT_EXPIRED,
        document_id="doc-abc",
    )
    assert events[0]["event_key"] == expected_key


def test_p1_same_runtime_snapshot_same_event_key() -> None:
    past = (date.today() - timedelta(days=1)).isoformat()
    runtime = evaluate_document_runtime(
        {"type": "passport", "status": "approved", "has_files": True, "expires_on": past},
        document_type_code="passport",
        reference_date=date.today(),
    )
    base = {
        "tenant_id": "tenant-1",
        "owner_type": "candidate",
        "owner_id": "cand-1",
        "document_runtime": runtime,
        "expires_on": past,
    }
    events = evaluate_document_expiry_events([base])
    assert len(events) == 1
    again = evaluate_document_expiry_events([dict(base)])
    assert again[0]["event_key"] == events[0]["event_key"]
    assert again[0]["event_code"] == events[0]["event_code"]


def test_p1_evaluator_does_not_recompute_expiry_from_raw_dates() -> None:
    """Trust runtime expiry_status — ignore raw date if runtime says valid."""
    future = (date.today() + timedelta(days=5)).isoformat()
    runtime = {
        "evaluation_version": DOCUMENT_RUNTIME_V1,
        "document_id": "doc-1",
        "document_type_code": "passport",
        "workflow_status": "approved",
        "expiry_status": "valid",
        "satisfies_requirement": True,
        "runtime_signal": None,
        "blockers": [],
        "warnings": [],
    }
    events = evaluate_document_expiry_events(
        [
            {
                "tenant_id": "tenant-1",
                "owner_type": "candidate",
                "owner_id": "cand-1",
                "expires_on": future,
                "document_runtime": runtime,
            }
        ]
    )
    assert events == []


def test_p1_from_runtime_delivery_contract() -> None:
    past = (date.today() - timedelta(days=2)).isoformat()
    soon = (date.today() + timedelta(days=7)).isoformat()
    docs = enrich_documents_via_contract(
        [
            {"type": "passport", "status": "approved", "has_files": True, "expires_on": past, "document_id": "d1"},
            {"type": "code95", "status": "approved", "has_files": True, "expires_on": soon, "document_id": "d2"},
            {"type": "driver_license", "status": "approved", "has_files": True, "expires_on": (date.today() + timedelta(days=90)).isoformat(), "document_id": "d3"},
        ]
    )
    delivery = build_instances_delivery_via_contract(docs)
    events = evaluate_expiry_events_from_runtime_delivery(
        delivery,
        owner_context={"tenant_id": "tenant-1", "owner_type": "candidate", "owner_id": "cand-1"},
    )
    codes = {event["event_code"] for event in events}
    assert codes == {EVENT_DOCUMENT_EXPIRED, EVENT_DOCUMENT_EXPIRING_SOON}
    assert all(event["source_layer"] == SOURCE_LAYER for event in events)
