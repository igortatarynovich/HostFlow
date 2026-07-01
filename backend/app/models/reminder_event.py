"""Legacy ``ReminderEvent`` re-export — ``ReminderEvent is ActivityEvent``.

Phase 1.3 (``activity_layer_v1`` Alembic revision) renames the audit-log
table from ``reminder_events`` to ``activity_events`` and the FK column
from ``reminder_id`` to ``activity_id``. The canonical ORM lives in
``backend.app.models.activity_event.ActivityEvent`` and exposes a
``reminder_id`` attribute synonym so callers that still use the old
keyword can continue to construct rows unchanged.

This module exists purely so existing imports
(``from backend.app.models.reminder_event import ReminderEvent``)
keep working — there is *one* mapper and *one* class with two names,
matching the same `Reminder is Activity` pattern used by
``models/reminder.py``. Phase 4 cleanup will retire this re-export.
"""

from __future__ import annotations

from .activity_event import ActivityEvent

ReminderEvent = ActivityEvent

__all__ = ["ReminderEvent"]
