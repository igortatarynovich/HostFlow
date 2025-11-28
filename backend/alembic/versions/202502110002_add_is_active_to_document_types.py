"""Add is_active flag to document_types.

Revision ID: 202502110002_add_is_active_to_document_types
Revises: 202502110001_align_documents_schema
Create Date: 2025-02-11 12:15:00.000000
"""

from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "202502110002_add_is_active_to_document_types"
down_revision: str | None = "202502110001_align_documents_schema"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _database_url() -> str:
    env_url = os.environ.get("DATABASE_URL") or os.environ.get("SYNC_DATABASE_URL")
    if env_url:
        return env_url
    return "sqlite:///app.db"


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table});").fetchall()
        return any(row[1] == column for row in rows)
    # PostgreSQL / others via information_schema
    row = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :t
              AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return bool(row)


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"
    default_true = sa.text("1") if is_sqlite else sa.text("true")

    with op.batch_alter_table("document_types", recreate="always") as batch:
        if _has_column("document_types", "is_active"):
            batch.alter_column(
                "is_active",
                existing_type=sa.Boolean(),
                nullable=False,
                server_default=default_true,
            )
        else:
            batch.add_column(
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=default_true,
                )
            )

    # Normalize existing NULLs just in case (older DBs)
    if is_sqlite:
        conn.execute(text("UPDATE document_types SET is_active = 1 WHERE is_active IS NULL"))
    else:
        conn.execute(text("UPDATE document_types SET is_active = true WHERE is_active IS NULL"))


def downgrade() -> None:
    with op.batch_alter_table("document_types", recreate="always") as batch:
        if _has_column("document_types", "is_active"):
            batch.drop_column("is_active")
