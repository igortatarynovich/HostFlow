"""Regression: unread notifications partial indexes exist (poll + dedupe)."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from backend.app.db.session import async_session_maker

REQUIRED_INDEXES = (
    "ix_notifications_unread_user_created",
    "ix_notifications_unread_user_type_channel_created",
    "ix_notifications_retention_read_created",
    "ix_notifications_retention_unread_created",
    "ix_notifications_retention_critical_created",
)


@pytest.mark.asyncio
async def test_notifications_unread_partial_indexes_present() -> None:
    """Alembic + ORM must expose the unread poll/dedupe partial indexes."""
    async with async_session_maker() as session:
        bind = session.get_bind()
        dialect = bind.dialect.name
        if dialect == "postgresql":
            rows = (
                await session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename = 'notifications'"
                    )
                )
            ).scalars().all()
            present = set(rows)
        else:
            insp = inspect(bind)
            if "notifications" not in insp.get_table_names():
                pytest.skip("notifications table missing")
            present = {ix["name"] for ix in insp.get_indexes("notifications")}

        missing = [name for name in REQUIRED_INDEXES if name not in present]
        assert not missing, f"missing notifications indexes: {missing}; have={sorted(present)}"


@pytest.mark.asyncio
async def test_notifications_unread_list_index_is_partial_unread() -> None:
    """List index must be partial on is_read = false (Postgres)."""
    async with async_session_maker() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("partial index predicate check is Postgres-only")
        row = (
            await session.execute(
                text(
                    """
                    SELECT pg_get_indexdef(i.oid) AS def
                    FROM pg_class t
                    JOIN pg_index x ON x.indrelid = t.oid
                    JOIN pg_class i ON i.oid = x.indexrelid
                    WHERE t.relname = 'notifications'
                      AND i.relname = 'ix_notifications_unread_user_created'
                    """
                )
            )
        ).mappings().one_or_none()
        assert row is not None, "ix_notifications_unread_user_created missing"
        defn = str(row["def"]).lower()
        assert "is_read" in defn and "false" in defn
        assert "tenant_id" in defn and "user_id" in defn and "created_at" in defn
