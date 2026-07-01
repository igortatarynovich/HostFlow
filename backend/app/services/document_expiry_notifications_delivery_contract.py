"""Service-layer facade for Document Expiry Notifications evaluator + registry + sync."""

from __future__ import annotations

from backend.app.document_expiry_notifications.evaluator import (
    build_expiry_event_key,
    evaluate_document_expiry_events,
    evaluate_expiry_events_from_runtime_delivery,
)
from backend.app.document_expiry_notifications.event_registry import (
    count_notification_events,
    empty_sync_summary,
    get_notification_event,
    list_notification_events,
    notification_event_to_dict,
    sync_document_expiry_events,
    sync_document_expiry_events_with_summary,
    update_notification_event_status,
    upsert_notification_event,
    upsert_notification_event_with_action,
    upsert_notification_events,
)
from backend.app.document_expiry_notifications.sync_job import (
    collect_candidate_runtime_snapshots,
    sync_document_expiry_notification_events,
)

__all__ = [
    "build_expiry_event_key",
    "collect_candidate_runtime_snapshots",
    "count_notification_events",
    "empty_sync_summary",
    "evaluate_document_expiry_events",
    "evaluate_expiry_events_from_runtime_delivery",
    "get_notification_event",
    "list_notification_events",
    "notification_event_to_dict",
    "sync_document_expiry_events",
    "sync_document_expiry_events_with_summary",
    "sync_document_expiry_notification_events",
    "update_notification_event_status",
    "upsert_notification_event",
    "upsert_notification_event_with_action",
    "upsert_notification_events",
]
