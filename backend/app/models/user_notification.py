"""Legacy import path for the canonical :class:`Notification` ORM model.

Phase 1.3 / ADR-012 renames the physical table to ``notifications`` and exposes
``user_notifications`` as a **read-only SQL view** in PostgreSQL. Code must not
map an ORM model to ``user_notifications`` — inserts would hit the rejecting
INSTEAD OF trigger.

``UserNotification`` remains a stable alias for :class:`~app.models.notification.Notification`
so existing imports keep working while writes go to ``notifications``.

Use a relative import here so Docker/runtime does not resolve ``backend.app.models``
(a duplicate package path) and re-enter ``models.__init__`` while this submodule is
still loading (circular import / ``partially initialized module``).
"""

from __future__ import annotations

from .notification import Notification

UserNotification = Notification

__all__ = ["UserNotification"]
