"""Service-layer facade for Document Expiry Notifications evaluator + registry."""

from __future__ import annotations

from backend.app.document_expiry_notifications.evaluator import (
    build_expiry_event_key,
    evaluate_document_expiry_events,
    evaluate_expiry_events_from_runtime_delivery,
)
from backend.app.document_expiry_notifications.event_registry import (
    count_notification_events,
    get_notification_event,
    list_notification_events,
    notification_event_to_dict,
    sync_document_expiry_events,
    update_notification_event_status,
    upsert_notification_event,
    upsert_notification_events,
)

__all__ = [
    "build_expiry_event_key",
    "count_notification_events",
    "get_notification_event",
    "evaluate_document_expiry_events",
    "evaluate_expiry_events_from_runtime_delivery",
    "list_notification_events",
    "notification_event_to_dict",
    "sync_document_expiry_events",
    "update_notification_event_status",
    "upsert_notification_event",
    "upsert_notification_events",
]
