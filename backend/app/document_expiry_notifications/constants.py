"""Document Expiry Notifications constants."""

from __future__ import annotations

from typing import Literal
NOTIFICATION_EVENT_V1 = "notification_event_v1"
SOURCE_LAYER = "document_expiry_notifications"

EVENT_DOCUMENT_EXPIRING_SOON = "document_expiring_soon"
EVENT_DOCUMENT_EXPIRED = "document_expired"

DEFAULT_EXPIRING_SOON_DAYS = 30

SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

EVENT_STATUS_OPEN = "open"
EVENT_STATUS_RESOLVED = "resolved"
EVENT_STATUS_IGNORED = "ignored"

VALID_EVENT_STATUSES = frozenset(
    {EVENT_STATUS_OPEN, EVENT_STATUS_RESOLVED, EVENT_STATUS_IGNORED}
)

UpsertAction = Literal["created", "updated", "skipped"]

# P1: expiry events only for operationally accepted documents.
EXPIRY_ELIGIBLE_WORKFLOW_STATUSES = frozenset({"approved"})
