"""Activity model — canonical entity of the Activity & Notification Operating Layer.

Source of truth for the unified work-item entity introduced by ADR-012
(``docs/specs/architecture/ADR-012-activity-notification-operating-layer.md``)
and the canon spec
(``docs/specs/architecture/activity-notification-operating-layer.md``).

This module backs Phase 1.3 (``activity_layer_v1`` Alembic revision):

- ``__tablename__ = "activities"`` (renamed from ``reminders``).
- Canonical column names: ``related_entity_type``, ``related_entity_id``,
  ``assigned_to_user_id``, ``created_by_user_id``, ``reminder_at``,
  ``metadata`` (Python attribute ``metadata_`` — see §9.0 of the migration
  plan: ``metadata`` is reserved by SQLAlchemy Declarative).
- New columns: ``company_id``, ``source_module``, ``starts_at``,
  ``sla_due_at``, ``sla_status``.

Legacy attribute synonyms (kept until Phase 4 cleanup — Constraint #4
of the Phase 1.3 migration plan):

- ``Activity.entity_type``       → ``Activity.related_entity_type``
- ``Activity.entity_id``         → ``Activity.related_entity_id``
- ``Activity.assignee_id``       → ``Activity.assigned_to_user_id``
- ``Activity.created_by``        → ``Activity.created_by_user_id``
- ``Activity.remind_at``         → ``Activity.reminder_at``
- ``Activity.payload``           → ``Activity.metadata_``

Both halves of every synonym work for ORM reads, writes **and** SQL
filter expressions — see ``docs/specs/architecture/phase-1-3-activity-layer-v1-migration-plan.md`` §9.

The legacy ``Reminder`` name remains a thin re-export
(``models/reminder.py``) so existing code that does
``from backend.app.models import Reminder`` continues to work, with
``Reminder is Activity`` (one mapper, one class, two names).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, synonym

from backend.app.db.base import Base
from .mixins import TimestampMixin


class ActivityStatus:
    """Canonical Activity status values (ADR-012 §6).

    Closed enumeration:
        ``planned``      — created, scheduled (replaces legacy ``new`` / ``pending`` / ``sent``).
        ``in_progress``  — actively being worked on (forward-only; introduced in Phase 1.3).
        ``done``         — completed.
        ``cancelled``    — cancelled.
        ``overdue``      — past ``due_at`` and not done.

    Legacy values (``new`` / ``pending`` / ``sent``) are collapsed into
    ``planned`` by the ``activity_layer_v1`` migration (§3 of the plan).
    They remain importable as constants for any in-flight code that
    still emits them; the service layer normalises them on write.
    """

    planned = "planned"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"
    overdue = "overdue"

    new = "new"
    pending = "pending"
    sent = "sent"


class ActivitySlaStatus:
    """Canonical Activity SLA status (ADR-012 §6, canon §3.1)."""

    ok = "ok"
    warning = "warning"
    breached = "breached"


class Activity(Base, TimestampMixin):
    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_tenant_due", "tenant_id", "due_at"),
        Index(
            "ix_activities_related_entity",
            "tenant_id",
            "related_entity_type",
            "related_entity_id",
        ),
        Index(
            "ix_activities_assignee_reminder",
            "tenant_id",
            "assigned_to_user_id",
            "reminder_at",
        ),
        Index(
            "ix_activities_assignee_due",
            "tenant_id",
            "assigned_to_user_id",
            "due_at",
        ),
        Index("ix_activities_status_due", "tenant_id", "status", "due_at"),
        Index("ix_activities_tenant_company", "tenant_id", "company_id"),
        Index("ix_activities_tenant_source", "tenant_id", "source_module"),
        Index(
            "ix_activities_tenant_sla",
            "tenant_id",
            "sla_status",
            "sla_due_at",
        ),
        Index("ix_activities_tenant_starts", "tenant_id", "starts_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_module: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    related_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    related_entity_id: Mapped[str] = mapped_column(String(120), nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # Phase 2.6.G-5 Stage E — FK ``users.id ON DELETE SET NULL`` is preserved
    # through the rename. Deleting a user clears orphan activity assignees
    # instead of leaving dangling UUIDs in /app/tasks and the bell.
    assigned_to_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, default="internal"
    )

    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reminder_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    snoozed_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    sla_due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    recurrence_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ActivityStatus.planned
    )

    # Canonical JSON column. Python attribute is ``metadata_`` because
    # ``metadata`` is reserved by SQLAlchemy Declarative — see §9.0 of the
    # Phase 1.3 migration plan. Legacy attribute ``payload`` is provided
    # below as a synonym (Constraint #4).
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # ---- Legacy attribute synonyms (Phase 1.3 §9.1, kept until Phase 4) ----
    entity_type = synonym("related_entity_type")
    entity_id = synonym("related_entity_id")
    assignee_id = synonym("assigned_to_user_id")
    created_by = synonym("created_by_user_id")
    remind_at = synonym("reminder_at")
    payload = synonym("metadata_")


__all__ = ["Activity", "ActivityStatus", "ActivitySlaStatus"]
