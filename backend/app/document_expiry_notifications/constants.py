"""Document Expiry Notifications constants."""

from __future__ import annotations

NOTIFICATION_EVENT_V1 = "notification_event_v1"
SOURCE_LAYER = "document_expiry_notifications"

EVENT_DOCUMENT_EXPIRING_SOON = "document_expiring_soon"
EVENT_DOCUMENT_EXPIRED = "document_expired"

DEFAULT_EXPIRING_SOON_DAYS = 30

SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

# P1: expiry events only for operationally accepted documents.
EXPIRY_ELIGIBLE_WORKFLOW_STATUSES = frozenset({"approved"})
