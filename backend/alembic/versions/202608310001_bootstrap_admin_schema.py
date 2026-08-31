"""Align the native role enum and preferences default with the persisted contract.

Revision ID: 202608310001_bootstrap_admin_schema
Revises: 202608250002_merge_e5_drop_and_adr036_heads

``superadmin`` is a canonical persisted trust role ([ADR-036] four-trust-roles
§1 and §5: ``users.role`` is ``superadmin|administrator|employee|viewer``).
The Python ``Role`` enum already has that member. The native PostgreSQL
``role`` type never received the label: ``NEW_ROLES`` in
``202512010200_admin_v2`` stopped at administrator/supervisor/recruiter/viewer,
and later slices added job-lane values, not the platform role.

``users.preferences`` is the ADR-036 bag for ``preset_id`` / ``access_context``.
The ORM column is ``nullable=False, default=dict``; register writes ``{}``.
A raw INSERT that omits the column must still produce that empty object, so
the server default is a schema invariant, not a seed-only patch.

Measured on a freshly migrated Postgres 16 (OL-2B, 2026-08-31):

    ERROR: invalid input value for enum role: "superadmin"
    ERROR: null value in column "preferences" of relation "users" ...

Expand-only: ADD VALUE and a default. Rollback class: artefact-reversible.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202608310001_bootstrap_admin_schema"
down_revision: Union[str, None] = "202608250002_merge_e5_drop_and_adr036_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pg_enum_type_for_column(conn, table: str, column: str) -> str | None:
    row = conn.execute(
        sa.text(
            """
            SELECT pg_type.typname
            FROM pg_attribute
            JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
            JOIN pg_type ON pg_type.oid = pg_attribute.atttypid
            WHERE pg_class.relname = :t
              AND pg_attribute.attname = :c
              AND pg_type.typtype = 'e'
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return str(row[0]) if row and row[0] else None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        enum_type = _pg_enum_type_for_column(conn, "users", "role")
        if enum_type:
            ctx = op.get_context()
            with ctx.autocommit_block():
                conn.exec_driver_sql(
                    f"ALTER TYPE {enum_type} ADD VALUE IF NOT EXISTS 'superadmin';"
                )
        insp = sa.inspect(conn)
        cols = {c["name"]: c for c in insp.get_columns("users")} if insp.has_table("users") else {}
        pref = cols.get("preferences")
        if pref is not None and pref.get("default") is None:
            op.execute(sa.text("ALTER TABLE users ALTER COLUMN preferences SET DEFAULT '{}'::jsonb"))
        return

    # SQLite / other: preferences default only
    insp = sa.inspect(conn)
    if insp.has_table("users"):
        cols = {c["name"] for c in insp.get_columns("users")}
        if "preferences" in cols:
            op.execute(sa.text("UPDATE users SET preferences = '{}' WHERE preferences IS NULL"))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TABLE users ALTER COLUMN preferences DROP DEFAULT"))
    # ENUM values cannot be dropped safely; leave superadmin in place.
