"""calendar_* tables explicit (Phase 1.0 / ADR-012).

Revision ID: 202607150001_cal
Revises: 202605100002_cas

Phase 1.0 of the Activity & Notification Operating Layer rollout
(see ``docs/specs/architecture/ADR-012-activity-notification-operating-layer.md``
and canon ``docs/specs/architecture/activity-notification-operating-layer.md`` §7.5).

Until now, the seven calendar/integration tables — ``calendar_connections``,
``calendar_channels``, ``calendar_items``, ``calendar_item_links``,
``calendar_sync_cursors``, ``calendar_sync_jobs`` and ``integration_action_logs``
— have only been created via ``Base.metadata.create_all`` /
``backend.app.services.ensure_calendar_schema`` at app start-up. There is no
canonical Alembic baseline for them, which means freshly-imaged Postgres
databases that *don't* run the bootstrap helper end up missing the tables, and
the alembic graph hides a piece of the production schema.

This revision records the existing schema as an explicit, idempotent baseline:

- It is **not destructive**: every ``CREATE TABLE`` / ``CREATE INDEX`` is
  guarded by ``IF NOT EXISTS`` so the migration is a no-op on environments
  where the bootstrap helper already provisioned the tables (dev sqlite, the
  vast majority of the prod fleet).
- ``downgrade()`` drops the tables / indexes only ``IF EXISTS``, so it can run
  on top of either a freshly-baselined DB or one that pre-dated this revision.
- Column types match ``backend/app/models/calendar_integration.py`` 1-to-1.
  ``payload``-style columns use ``JSONB`` on Postgres and fall back to ``JSON``
  elsewhere (sqlite local dev).

The migration deliberately does **not** delete or rewire ``ensure_calendar_schema``
yet — that helper still runs and remains a safety net for sqlite local dev
plus any prod shard that might have been imaged without alembic. Removing
that helper is a follow-up after Phase 2 stabilises (own ticket).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202607150001_cal"
down_revision: Union[str, None] = "202605100002_cas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in set(insp.get_table_names())


def _has_index(conn: sa.Connection, table: str, index: str) -> bool:
    insp = sa.inspect(conn)
    try:
        existing = {ix["name"] for ix in insp.get_indexes(table)}
    except Exception:
        return False
    return index in existing


def _json_type() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _create_calendar_connections(conn: sa.Connection) -> None:
    if not _has_table(conn, "calendar_connections"):
        op.create_table(
            "calendar_connections",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=True),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("account_ref", sa.String(255), nullable=True),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
            sa.Column("scopes_json", _json_type(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("token_meta_json", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("last_error", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    for name, cols in (
        ("ix_calendar_connections_tenant_provider", ("tenant_id", "provider", "status")),
        ("ix_calendar_connections_tenant_user", ("tenant_id", "user_id", "status")),
        ("ix_calendar_connections_tenant_id", ("tenant_id",)),
        ("ix_calendar_connections_user_id", ("user_id",)),
    ):
        if not _has_index(conn, "calendar_connections", name):
            op.create_index(name, "calendar_connections", list(cols))


def _create_calendar_channels(conn: sa.Connection) -> None:
    if not _has_table(conn, "calendar_channels"):
        op.create_table(
            "calendar_channels",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("connection_id", sa.String(36), nullable=False),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("resource_id", sa.String(255), nullable=True),
            sa.Column("channel_ref", sa.String(255), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("renew_after", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "health_state",
                sa.String(32),
                nullable=False,
                server_default=sa.text("'healthy'"),
            ),
            sa.Column("payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    for name, cols in (
        ("ix_calendar_channels_conn_provider", ("connection_id", "provider", "health_state")),
        ("ix_calendar_channels_tenant_expires", ("tenant_id", "expires_at")),
        ("ix_calendar_channels_tenant_id", ("tenant_id",)),
        ("ix_calendar_channels_connection_id", ("connection_id",)),
    ):
        if not _has_index(conn, "calendar_channels", name):
            op.create_index(name, "calendar_channels", list(cols))


def _create_calendar_items(conn: sa.Connection) -> None:
    if not _has_table(conn, "calendar_items"):
        op.create_table(
            "calendar_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(36), nullable=True),
            sa.Column("assignee_id", sa.String(36), nullable=True),
            sa.Column("kind", sa.String(32), nullable=False, server_default=sa.text("'event'")),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'scheduled'")),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("timezone", sa.String(64), nullable=False, server_default=sa.text("'UTC'")),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("all_day", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("linked_entity_type", sa.String(64), nullable=True),
            sa.Column("linked_entity_id", sa.String(120), nullable=True),
            sa.Column("source", sa.String(32), nullable=False, server_default=sa.text("'hostflow'")),
            sa.Column("payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    for name, cols in (
        ("ix_calendar_items_tenant_start", ("tenant_id", "starts_at")),
        ("ix_calendar_items_tenant_owner", ("tenant_id", "owner_id", "starts_at")),
        ("ix_calendar_items_tenant_kind_status", ("tenant_id", "kind", "status", "starts_at")),
        ("ix_calendar_items_tenant_entity", ("tenant_id", "linked_entity_type", "linked_entity_id")),
        ("ix_calendar_items_tenant_id", ("tenant_id",)),
        ("ix_calendar_items_owner_id", ("owner_id",)),
        ("ix_calendar_items_assignee_id", ("assignee_id",)),
    ):
        if not _has_index(conn, "calendar_items", name):
            op.create_index(name, "calendar_items", list(cols))


def _create_calendar_item_links(conn: sa.Connection) -> None:
    if not _has_table(conn, "calendar_item_links"):
        op.create_table(
            "calendar_item_links",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("calendar_item_id", sa.String(36), nullable=False),
            sa.Column("connection_id", sa.String(36), nullable=True),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("provider_calendar_id", sa.String(255), nullable=True),
            sa.Column("provider_event_id", sa.String(255), nullable=False),
            sa.Column("provider_version", sa.String(255), nullable=True),
            sa.Column("sync_state", sa.String(32), nullable=False, server_default=sa.text("'synced'")),
            sa.Column("payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    for name, cols in (
        ("ix_calendar_item_links_item_provider", ("calendar_item_id", "provider")),
        ("ix_calendar_item_links_provider_event", ("provider", "provider_event_id")),
        ("ix_calendar_item_links_tenant_state", ("tenant_id", "sync_state", "updated_at")),
        ("ix_calendar_item_links_tenant_id", ("tenant_id",)),
        ("ix_calendar_item_links_calendar_item_id", ("calendar_item_id",)),
        ("ix_calendar_item_links_connection_id", ("connection_id",)),
    ):
        if not _has_index(conn, "calendar_item_links", name):
            op.create_index(name, "calendar_item_links", list(cols))


def _create_calendar_sync_cursors(conn: sa.Connection) -> None:
    if not _has_table(conn, "calendar_sync_cursors"):
        op.create_table(
            "calendar_sync_cursors",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("connection_id", sa.String(36), nullable=False),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("calendar_ref", sa.String(255), nullable=True),
            sa.Column("cursor", sa.Text, nullable=True),
            sa.Column("cursor_meta_json", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    for name, cols in (
        ("ix_calendar_sync_cursors_connection", ("connection_id", "provider", "calendar_ref")),
        ("ix_calendar_sync_cursors_tenant_id", ("tenant_id",)),
        ("ix_calendar_sync_cursors_connection_id", ("connection_id",)),
    ):
        if not _has_index(conn, "calendar_sync_cursors", name):
            op.create_index(name, "calendar_sync_cursors", list(cols))


def _create_calendar_sync_jobs(conn: sa.Connection) -> None:
    if not _has_table(conn, "calendar_sync_jobs"):
        op.create_table(
            "calendar_sync_jobs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("source_kind", sa.String(64), nullable=False),
            sa.Column("operation", sa.String(32), nullable=False, server_default=sa.text("'ingest'")),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'queued'")),
            sa.Column("dedupe_key", sa.String(255), nullable=True),
            sa.Column("retry_count", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text, nullable=True),
            sa.Column("payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    for name, cols in (
        ("ix_calendar_sync_jobs_tenant_status", ("tenant_id", "status", "created_at")),
        ("ix_calendar_sync_jobs_tenant_source", ("tenant_id", "source_kind", "created_at")),
        ("ix_calendar_sync_jobs_dedupe", ("dedupe_key",)),
        ("ix_calendar_sync_jobs_tenant_id", ("tenant_id",)),
    ):
        if not _has_index(conn, "calendar_sync_jobs", name):
            op.create_index(name, "calendar_sync_jobs", list(cols))


def _create_integration_action_logs(conn: sa.Connection) -> None:
    if not _has_table(conn, "integration_action_logs"):
        op.create_table(
            "integration_action_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("calendar_item_id", sa.String(36), nullable=True),
            sa.Column("source", sa.String(32), nullable=False, server_default=sa.text("'hostflow'")),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("actor_user_id", sa.String(36), nullable=True),
            sa.Column("idempotency_key", sa.String(255), nullable=True),
            sa.Column("payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("outcome", _json_type(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    for name, cols in (
        ("ix_integration_action_logs_tenant_created", ("tenant_id", "created_at")),
        ("ix_integration_action_logs_tenant_source", ("tenant_id", "source", "created_at")),
        ("ix_integration_action_logs_tenant_item", ("tenant_id", "calendar_item_id", "created_at")),
        ("ix_integration_action_logs_tenant_id", ("tenant_id",)),
        ("ix_integration_action_logs_calendar_item_id", ("calendar_item_id",)),
        ("ix_integration_action_logs_actor_user_id", ("actor_user_id",)),
    ):
        if not _has_index(conn, "integration_action_logs", name):
            op.create_index(name, "integration_action_logs", list(cols))


# Indexes that need to be dropped before their parent table — they are
# attached to the table in upgrade() above, but Postgres allows index DROP
# without table DROP. We list them explicitly so downgrade is symmetric and
# does not rely on CASCADE.
_INDEXES_TO_DROP: tuple[tuple[str, str], ...] = (
    ("calendar_connections", "ix_calendar_connections_tenant_provider"),
    ("calendar_connections", "ix_calendar_connections_tenant_user"),
    ("calendar_connections", "ix_calendar_connections_tenant_id"),
    ("calendar_connections", "ix_calendar_connections_user_id"),
    ("calendar_channels", "ix_calendar_channels_conn_provider"),
    ("calendar_channels", "ix_calendar_channels_tenant_expires"),
    ("calendar_channels", "ix_calendar_channels_tenant_id"),
    ("calendar_channels", "ix_calendar_channels_connection_id"),
    ("calendar_items", "ix_calendar_items_tenant_start"),
    ("calendar_items", "ix_calendar_items_tenant_owner"),
    ("calendar_items", "ix_calendar_items_tenant_kind_status"),
    ("calendar_items", "ix_calendar_items_tenant_entity"),
    ("calendar_items", "ix_calendar_items_tenant_id"),
    ("calendar_items", "ix_calendar_items_owner_id"),
    ("calendar_items", "ix_calendar_items_assignee_id"),
    ("calendar_item_links", "ix_calendar_item_links_item_provider"),
    ("calendar_item_links", "ix_calendar_item_links_provider_event"),
    ("calendar_item_links", "ix_calendar_item_links_tenant_state"),
    ("calendar_item_links", "ix_calendar_item_links_tenant_id"),
    ("calendar_item_links", "ix_calendar_item_links_calendar_item_id"),
    ("calendar_item_links", "ix_calendar_item_links_connection_id"),
    ("calendar_sync_cursors", "ix_calendar_sync_cursors_connection"),
    ("calendar_sync_cursors", "ix_calendar_sync_cursors_tenant_id"),
    ("calendar_sync_cursors", "ix_calendar_sync_cursors_connection_id"),
    ("calendar_sync_jobs", "ix_calendar_sync_jobs_tenant_status"),
    ("calendar_sync_jobs", "ix_calendar_sync_jobs_tenant_source"),
    ("calendar_sync_jobs", "ix_calendar_sync_jobs_dedupe"),
    ("calendar_sync_jobs", "ix_calendar_sync_jobs_tenant_id"),
    ("integration_action_logs", "ix_integration_action_logs_tenant_created"),
    ("integration_action_logs", "ix_integration_action_logs_tenant_source"),
    ("integration_action_logs", "ix_integration_action_logs_tenant_item"),
    ("integration_action_logs", "ix_integration_action_logs_tenant_id"),
    ("integration_action_logs", "ix_integration_action_logs_calendar_item_id"),
    ("integration_action_logs", "ix_integration_action_logs_actor_user_id"),
)


_TABLES_TO_DROP: tuple[str, ...] = (
    "integration_action_logs",
    "calendar_sync_jobs",
    "calendar_sync_cursors",
    "calendar_item_links",
    "calendar_items",
    "calendar_channels",
    "calendar_connections",
)


def upgrade() -> None:
    conn = op.get_bind()
    _create_calendar_connections(conn)
    _create_calendar_channels(conn)
    _create_calendar_items(conn)
    _create_calendar_item_links(conn)
    _create_calendar_sync_cursors(conn)
    _create_calendar_sync_jobs(conn)
    _create_integration_action_logs(conn)


def downgrade() -> None:
    """Idempotent downgrade.

    We drop indexes first (only if they exist) and then tables (only if they
    exist). This is safe whether the calendar tables were created by this
    revision, by ``ensure_calendar_schema``, or by ``Base.metadata.create_all``
    on a freshly-imaged dev DB. Existing rows are destroyed, but Phase 1.0 is
    purely a baseline revision — no live customer data was migrated **into**
    these tables by this revision, so downgrade is reversible by re-running
    ``upgrade()`` (or by re-running the bootstrap helper).
    """

    conn = op.get_bind()

    for table, index in _INDEXES_TO_DROP:
        if _has_index(conn, table, index):
            op.drop_index(index, table_name=table)

    for table in _TABLES_TO_DROP:
        if _has_table(conn, table):
            op.drop_table(table)
