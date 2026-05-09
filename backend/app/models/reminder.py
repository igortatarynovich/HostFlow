"""Legacy ``Reminder`` re-export — ``Reminder is Activity``.

Phase 1.3 (``activity_layer_v1`` Alembic revision) renames the
``reminders`` table to ``activities`` and the audit log
``reminder_events`` to ``activity_events``. The canonical ORM lives in
``backend.app.models.activity.Activity`` and exposes the legacy
attribute names (``entity_type``, ``entity_id``, ``assignee_id``,
``created_by``, ``remind_at``, ``payload``) as SQLAlchemy synonyms so
existing queries keep working byte-for-byte.

This module exists so existing imports
(``from backend.app.models.reminder import Reminder, ReminderStatus``)
keep working — there is *one* mapper and *one* class with two names,
matching the same ``ReminderEvent is ActivityEvent`` pattern in
``models/reminder_event.py``. Phase 4 cleanup will retire this
re-export — see
``docs/specs/architecture/phase-1-3-activity-layer-v1-migration-plan.md``
§9.1 and ``docs/specs/architecture/ADR-012-activity-notification-operating-layer.md``.

``ReminderStatus`` is preserved as the legacy alias for
``ActivityStatus`` so call sites that still emit ``ReminderStatus.new``
/ ``pending`` / ``sent`` continue to compile. The values themselves
are normalised on read by the migration (``new`` / ``pending`` /
``sent`` collapse to ``planned``).
"""

from __future__ import annotations

from .activity import Activity, ActivityStatus

Reminder = Activity
ReminderStatus = ActivityStatus

__all__ = ["Reminder", "ReminderStatus"]
