"""Notification model — canonical signal entity of the Activity & Notification Operating Layer.

Source of truth for the unified user-facing notification entity introduced
by ADR-012 (``docs/specs/architecture/ADR-012-activity-notification-operating-layer.md``).
A ``Notification`` is a **signal to a user** about something that
happened or needs attention. It is intentionally distinct from
``Activity`` (the work item) and links to one via ``activity_id``.

Phase 1.3 (``activity_layer_v1``) renames the table from
``user_notifications`` to ``notifications`` and adds the canonical
fields: ``title``, ``body``, ``severity``, ``activity_id``.

Legacy attribute synonyms (kept until Phase 4 cleanup — Constraint #4
of the Phase 1.3 migration plan):

- ``Notification.event_type``  → ``Notification.type``
- ``Notification.entity_type`` → ``Notification.related_entity_type``
- ``Notification.entity_id``   → ``Notification.related_entity_id``
- ``Notification.payload``     → ``Notification.metadata_``

The legacy ``UserNotification`` name remains a thin re-export
(``models/user_notification.py``) — ``UserNotification is Notification``.

``severity`` is the closed enumeration ``info | warning | critical``
(see :class:`NotificationSeverity` and ADR-012 §6 / canon §3.3). The
legacy ``priority`` column is preserved through Phase 1.3 and only
dropped in Phase 4 cleanup (Constraint #4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, synonym

from backend.app.db.base import Base
from .mixins import now_utc

JSONType = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))


class NotificationSeverity:
    """Canonical Notification severity (ADR-012 §6, canon §3.3).

    Closed enumeration: ``info | warning | critical`` — exactly three
    values. We deliberately have **no** ``error`` tier: in product UX
    a fourth tier overlaps ``critical`` and creates ambiguity about
    which one demands immediate action. Legacy ``priority`` values
    such as ``error``, ``high``, ``urgent`` are collapsed onto these
    three on read (see ``activity_layer_v1`` migration §6.3).
    """

    info = "info"
    warning = "warning"
    critical = "critical"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_tenant_id", "tenant_id"),
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_type", "type"),
        Index(
            "ix_notifications_tenant_severity_unread",
            "tenant_id",
            "severity",
            "is_read",
        ),
        Index(
            "ix_notifications_tenant_activity",
            "tenant_id",
            "activity_id",
        ),
        Index(
            "ix_notifications_tenant_related_entity",
            "tenant_id",
            "related_entity_type",
            "related_entity_id",
        ),
        # Unread poll list: tenant+user + created_at, only unread rows.
        Index(
            "ix_notifications_unread_user_created",
            "tenant_id",
            "user_id",
            text("created_at DESC"),
            postgresql_where=text("is_read = false"),
            sqlite_where=text("is_read = 0"),
        ),
        # Unread dedupe / typed lookups.
        Index(
            "ix_notifications_unread_user_type_channel_created",
            "tenant_id",
            "user_id",
            "type",
            "channel",
            text("created_at DESC"),
            postgresql_where=text("is_read = false"),
            sqlite_where=text("is_read = 0"),
        ),
        Index(
            "uq_notifications_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
            sqlite_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)

    type: Mapped[str] = mapped_column(String(64), nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    related_entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    activity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(16), nullable=False, default="in_app", server_default=text("'in_app'")
    )
    # Stable insert identity for SLA/domain events (NULL = legacy / non-idempotent rows).
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(191), nullable=True)
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONType, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # ---- Legacy attribute synonyms (Phase 1.3 §9.1, kept until Phase 4) ----
    event_type = synonym("type")
    entity_type = synonym("related_entity_type")
    entity_id = synonym("related_entity_id")
    payload = synonym("metadata_")

    def mark_read(self, timestamp: Optional[datetime] = None) -> None:
        ts = timestamp or now_utc()
        self.is_read = True
        self.read_at = ts
        self.updated_at = ts


__all__ = ["Notification", "NotificationSeverity"]
