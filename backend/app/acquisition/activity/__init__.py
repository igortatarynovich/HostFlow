"""Acquisition Activity Timeline foundation (Stage 3E PR-1).

Public surface for PR-2 instrumentation (keep minimal):
- ``append_activity_event``
- ``list_activity_events``

Catalog helpers are read-only introspection. Internal repository getters are not
part of the stable public write/read contract.
"""

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import (
    ACTIVITY_EVENT_CATALOG,
    ACTIVITY_EVENT_TYPES,
    ActivityEventContract,
    get_activity_event_contract,
)
from backend.app.acquisition.activity.errors import (
    ActivityTimelineError,
    InvalidActivityActor,
    InvalidActivityPayload,
    UnknownActivityEventType,
    UnsupportedActivityEventVersion,
)
from backend.app.acquisition.activity.repository import (
    ACTIVITY_LIST_ORDER,
    list_activity_events,
)

__all__ = [
    "ACTIVITY_EVENT_CATALOG",
    "ACTIVITY_EVENT_TYPES",
    "ACTIVITY_LIST_ORDER",
    "ActivityEventContract",
    "ActivityTimelineError",
    "InvalidActivityActor",
    "InvalidActivityPayload",
    "UnknownActivityEventType",
    "UnsupportedActivityEventVersion",
    "append_activity_event",
    "get_activity_event_contract",
    "list_activity_events",
]
