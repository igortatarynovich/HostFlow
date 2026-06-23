"""Document Expiry Notifications — expiry event evaluation (P1)."""

from backend.app.document_expiry_notifications.constants import (
    DEFAULT_EXPIRING_SOON_DAYS,
    EVENT_DOCUMENT_EXPIRED,
    EVENT_DOCUMENT_EXPIRING_SOON,
    EVENT_STATUS_IGNORED,
    EVENT_STATUS_OPEN,
    EVENT_STATUS_RESOLVED,
    NOTIFICATION_EVENT_V1,
    SOURCE_LAYER,
)
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
    "DEFAULT_EXPIRING_SOON_DAYS",
    "EVENT_DOCUMENT_EXPIRED",
    "EVENT_DOCUMENT_EXPIRING_SOON",
    "EVENT_STATUS_IGNORED",
    "EVENT_STATUS_OPEN",
    "EVENT_STATUS_RESOLVED",
    "NOTIFICATION_EVENT_V1",
    "SOURCE_LAYER",
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
