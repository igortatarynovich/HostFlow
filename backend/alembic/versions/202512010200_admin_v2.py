"""Admin v2 core structures (RBAC, ACL, deletion workflow).

Revision ID: 202512010200_admin_v2
Revises: 202512010001_admin_users_module
Create Date: 2025-12-01 10:00:00.000000
"""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "202512010200_admin_v2"
down_revision = "202512010001_admin_users_module"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

NEW_ROLES = ("administrator", "supervisor", "recruiter", "viewer")
ROLE_MAP = {
    "admin": "administrator",
    "administrator": "administrator",
    "owner": "administrator",
    "manager": "supervisor",
    "supervisor": "supervisor",
    "recruiter": "recruiter",
    "viewer": "viewer",
}


def _table_exists(conn, name: str) -> bool:
    if conn.dialect.name == "sqlite":
        res = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        return res is not None
    res = conn.execute(
        sa.text("SELECT to_regclass(:n)"),
        {"n": name},
    ).fetchone()
    return res and res[0] is not None



def _has_column(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return any(r[1] == column for r in rows)
    res = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return res is not None


# Helper: get enum type name of a table column if it is ENUM (Postgres only)
def _pg_enum_type_of(conn, table: str, column: str) -> str | None:
    """Return enum type name of table.column if it is an ENUM, else None."""
    if conn.dialect.name != "postgresql":
        return None
    row = conn.execute(
        sa.text(
            """
            SELECT t.typname
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_type t ON t.oid = a.atttypid
            WHERE c.relname = :t AND a.attname = :c AND t.typtype = 'e'
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row[0] if row else None



def _ensure_role_values(conn) -> None:
    enum_type = _pg_enum_type_of(conn, "users", "role")
    if enum_type:
        # DDL в Postgres нельзя параметризовать. Используем exec_driver_sql и литералы.
        # Убедимся, что тип существует (страховка при повторных прогонах на чистой БД)
        conn.exec_driver_sql(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role') THEN
                    CREATE TYPE role AS ENUM ('owner');
                END IF;
            END
            $$;
            """
        )

        # Добавляем недостающие значения enum атомарно, без параметров
        ctx = op.get_context()
        with ctx.autocommit_block():
            for value in NEW_ROLES:
                conn.exec_driver_sql(
                    f"ALTER TYPE {enum_type} ADD VALUE IF NOT EXISTS '{value}';"
                )

        # Нормализуем данные users.role, здесь можно использовать параметры для значений,
        # но тип перечисления подставляем как литерал в CAST
        for old, new in ROLE_MAP.items():
            conn.execute(
                sa.text(
                    f"""
                    UPDATE users
                    SET role = CAST(:new_val AS {enum_type})
                    WHERE lower(role::text) = :old_val
                    """
                ),
                {"new_val": new, "old_val": old.lower()},
            )
    else:
        # Не-ENUM случай (sqlite/varchar)
        for old, new in ROLE_MAP.items():
            conn.execute(
                text(
                    """
                    UPDATE users
                    SET role = :new_role
                    WHERE lower(role) = :old_role
                    """
                ),
                {"new_role": new, "old_role": old.lower()},
            )


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    _ensure_role_values(conn)

    # Ensure role column accepts new values by recreating CHECK constraint for SQLite
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.alter_column(
                "role",
                existing_type=sa.String(length=32),
                type_=sa.String(length=32),
                nullable=False,
            )
    else:
        # PostgreSQL: ensure users.role enum has all required values
        enum_type = _pg_enum_type_of(conn, "users", "role")
        if enum_type:
            for value in NEW_ROLES:
                conn.exec_driver_sql(
                    f"ALTER TYPE {enum_type} ADD VALUE IF NOT EXISTS '{value}';"
                )

    # Users: supervisor_id + CHECK via batch (SQLite-safe)
    with op.batch_alter_table("users") as batch:
        if not _has_column(conn, "users", "supervisor_id"):
            batch.add_column(sa.Column("supervisor_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_users_supervisor_id_users",
                "users",
                ["supervisor_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if conn.dialect.name == "postgresql":
            batch.create_check_constraint(
                "ck_users_supervisor_role",
                "(supervisor_id IS NULL) OR (role::text = 'recruiter')",
            )
        else:
            batch.create_check_constraint(
                "ck_users_supervisor_role",
                "(supervisor_id IS NULL) OR (role = 'recruiter')",
            )

    op.create_index(
        "ix_users_tenant_role", "users", ["tenant_id", "role"], unique=False
    )
    op.create_index("ix_users_supervisor_id", "users", ["supervisor_id"], unique=False)

    if not _table_exists(conn, "user_company_access"):
        op.create_table(
            "user_company_access",
            sa.Column(
                "id",
                sa.String(length=36),
                primary_key=True,
                nullable=False,
                default=lambda: str(uuid.uuid4()),
            ),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column(
                "user_id",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "company_id",
                sa.String(length=36),
                sa.ForeignKey("companies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "can_edit",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0" if dialect == "sqlite" else "false"),
            ),
            sa.UniqueConstraint(
                "tenant_id", "user_id", "company_id", name="uq_user_company_access"
            ),
        )
        op.create_index(
            "ix_user_company_access_user",
            "user_company_access",
            ["tenant_id", "user_id"],
        )
        op.create_index(
            "ix_user_company_access_company",
            "user_company_access",
            ["tenant_id", "company_id"],
        )

    if not _table_exists(conn, "candidate_delete_requests"):
        op.create_table(
            "candidate_delete_requests",
            sa.Column(
                "id",
                sa.String(length=36),
                primary_key=True,
                nullable=False,
                default=lambda: str(uuid.uuid4()),
            ),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column(
                "candidate_id",
                sa.String(length=36),
                sa.ForeignKey("candidates.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "requested_by",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=False,
            ),
            sa.Column(
                "supervisor_id",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=False,
            ),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default="pending",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "resolved_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column(
                "resolved_by",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_candidate_delete_requests_tenant_status",
            "candidate_delete_requests",
            ["tenant_id", "status"],
        )
        op.create_index(
            "ix_candidate_delete_requests_supervisor",
            "candidate_delete_requests",
            ["tenant_id", "supervisor_id"],
        )
        op.create_index(
            "ix_candidate_delete_requests_candidate",
            "candidate_delete_requests",
            ["tenant_id", "candidate_id"],
        )
        if dialect == "sqlite":
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_candidate_delete_pending ON candidate_delete_requests "
                "(tenant_id, candidate_id) WHERE status = 'pending'"
            )
        else:
            op.create_index(
                "uq_candidate_delete_pending",
                "candidate_delete_requests",
                ["tenant_id", "candidate_id"],
                unique=True,
                postgresql_where=sa.text("status = 'pending'"),
            )

    if not _has_column(conn, "candidates", "deleted_at"):
        op.add_column(
            "candidates",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists(conn, "activity_log"):
        op.create_table(
            "activity_log",
            sa.Column(
                "id",
                sa.String(length=36),
                primary_key=True,
                nullable=False,
                default=lambda: str(uuid.uuid4()),
            ),
            sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column(
                "actor_id",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("target_type", sa.String(length=64), nullable=True),
            sa.Column("target_id", sa.String(length=36), nullable=True),
            sa.Column(
                "payload",
                    sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
                default=dict,
            ),
            sa.Column("ip", sa.String(length=64), nullable=True),
            sa.Column("ua", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_activity_log_tenant_created",
            "activity_log",
            ["tenant_id", "created_at"],
        )

    # Extend user_invites with supervisor metadata + companies JSON
    with op.batch_alter_table("user_invites") as batch:
        if not _has_column(conn, "user_invites", "supervisor_id"):
            batch.add_column(sa.Column("supervisor_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_user_invites_supervisor_id_users",
                "users",
                ["supervisor_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not _has_column(conn, "user_invites", "companies"):
            batch.add_column(
                sa.Column(
                    "companies",
                    sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                    nullable=True,
                    default=list,
                )
            )
        if not _has_column(conn, "user_invites", "used_at"):
            batch.add_column(
                sa.Column("used_at", sa.DateTime(timezone=True), nullable=True)
            )

    # Ensure metadata_json is JSON object, autopopulate for newly added columns
    conn.execute(
        text(
            """
            UPDATE user_invites
            SET metadata_json = COALESCE(metadata_json, :empty)
            """
        ),
        {"empty": json.dumps({})},
    )


def downgrade() -> None:
    # Downgrade is intentionally limited – raise explicit error.
    raise RuntimeError("Downgrade not supported for admin v2 migration")
