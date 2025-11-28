"""Align documents schema with HostFlow specification.

Revision ID: 202502110001_align_documents_schema
Revises: 20251021_add_candidate_profile_schema
Create Date: 2025-02-11 12:00:00.000000
"""

from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "202502110001_align_documents_schema"
down_revision: str | None = "20251021_add_candidate_profile_schema"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _database_url() -> str:
    env_url = os.environ.get("DATABASE_URL") or os.environ.get("SYNC_DATABASE_URL")
    if env_url:
        return env_url
    # fallback to local sqlite database used in dev/tests
    return "sqlite:///app.db"


def _has_column(table: str, column: str) -> bool:
    """
    Dialect-aware check that uses the CURRENT Alembic connection instead of
    opening a new engine (avoids env mismatch and placeholder issues).
    Works for PostgreSQL and SQLite.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        # PRAGMA table_info returns rows where second column is the column name
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table});").fetchall()
        return any(row[1] == column for row in rows)

    # Default branch: PostgreSQL (and others that expose information_schema)
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
    # drop legacy indexes that depend on the old column name before recreating the table
    for idx in ("ix_documents_key", "ix_documents_tenant_candidate_key"):
        try:
            op.drop_index(idx, table_name="documents")
        except Exception:
            pass

    with op.batch_alter_table("documents", recreate="always") as batch:
        # rename key -> type if still present
        if _has_column("documents", "key") and not _has_column("documents", "type"):
            batch.alter_column(
                "key",
                new_column_name="type",
                existing_type=sa.String(length=64),
                type_=sa.String(length=100),
                nullable=False,
            )

        # core business columns
        if not _has_column("documents", "number"):
            batch.add_column(sa.Column("number", sa.String(length=128), nullable=True))
        if not _has_column("documents", "files"):
            batch.add_column(sa.Column("files", sa.JSON(), nullable=True))
        if not _has_column("documents", "source"):
            batch.add_column(sa.Column("source", sa.String(length=64), nullable=True))
        if not _has_column("documents", "external_id"):
            batch.add_column(sa.Column("external_id", sa.String(length=128), nullable=True))
        if not _has_column("documents", "verified_at"):
            batch.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))

        # ensure reminder_days_before defaults to 30 (may be NULL in dumps)
        if _has_column("documents", "reminder_days_before"):
            batch.alter_column(
                "reminder_days_before",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("30"),
            )
        else:
            batch.add_column(
                sa.Column(
                    "reminder_days_before",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("30"),
                )
            )

        # tighten status default
        if _has_column("documents", "status"):
            batch.alter_column(
                "status",
                existing_type=sa.String(length=50),
                nullable=False,
                server_default=sa.text("'pending_validation'"),
            )
        else:
            batch.add_column(
                sa.Column(
                    "status",
                    sa.String(length=50),
                    nullable=False,
                    server_default=sa.text("'pending_validation'"),
                )
            )

        # owner columns should default to candidate for backwards compatibility
        if not _has_column("documents", "owner_type"):
            batch.add_column(
                sa.Column("owner_type", sa.String(length=50), nullable=True)
            )
        if not _has_column("documents", "owner_id"):
            batch.add_column(
                sa.Column("owner_id", sa.String(length=36), nullable=True)
            )

        if _has_column("documents", "owner_type"):
            batch.alter_column(
                "owner_type",
                existing_type=sa.String(length=50),
                nullable=True,
            )
        if _has_column("documents", "owner_id"):
            batch.alter_column(
                "owner_id",
                existing_type=sa.String(length=36),
                nullable=True,
            )

        # meta_json should stay text but ensure non-null default
        if _has_column("documents", "meta_json"):
            batch.alter_column(
                "meta_json",
                existing_type=sa.Text(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        else:
            batch.add_column(
                sa.Column(
                    "meta_json",
                    sa.Text(),
                    nullable=False,
                    server_default=sa.text("'{}'"),
                )
            )

        # drop legacy duplicate columns if they still exist
        for legacy in ("issued_date", "expires_date"):
            if _has_column("documents", legacy):
                batch.drop_column(legacy)

    # recreate indices with the new column name and additional helpers
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Use raw SQL to ensure IF NOT EXISTS is honored on both PG and SQLite.
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_type ON documents (type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_tenant_candidate_type ON documents (tenant_id, candidate_id, type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_expires_at ON documents (tenant_id, expires_at)")

    # data backfill
    conn = op.get_bind()
    dialect = conn.dialect.name
    is_sqlite = dialect == "sqlite"
    conn.execute(
        text(
            """
            UPDATE documents
            SET owner_type = COALESCE(owner_type, 'candidate'),
                owner_id = COALESCE(owner_id, candidate_id)
            """
        )
    )
    if dialect == "postgresql":
        conn.execute(
            text("UPDATE documents SET files = COALESCE(files, '[]'::json)")
        )
    else:
        conn.execute(
            text(
                """
                UPDATE documents
                SET files = CASE
                    WHEN files IS NULL OR trim(CAST(files AS TEXT)) = ''
                        THEN '[]'
                    ELSE files
                END
                """
            )
        )
    conn.execute(
        text(
            """
            UPDATE documents
            SET status = 'pending_validation'
            WHERE status IS NULL OR status = ''
            """
        )
    )

    # refresh triggers that maintain candidate.docs_progress
    if is_sqlite:
        for trig in (
            "trg_docs_after_insert",
            "trg_docs_after_update",
            "trg_docs_after_delete",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS {trig}")

        docs_progress_sql = """
            json_object(
                'total',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                ), 0),
                'with_files',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND (
                        (d.files IS NOT NULL AND json_valid(d.files) = 1 AND json_array_length(d.files) > 0)
                        OR (d.filename IS NOT NULL AND length(trim(d.filename)) > 0)
                        OR (d.path IS NOT NULL AND length(trim(d.path)) > 0)
                      )
                ), 0),
                'verified',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND lower(d.status) = 'verified'
                ), 0),
                'pending_validation',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND lower(d.status) = 'pending_validation'
                ), 0),
                'invalid',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND lower(d.status) = 'invalid'
                ), 0),
                'expired',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND lower(d.status) = 'expired'
                ), 0),
                'ready',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND lower(d.status) = 'verified'
                ), 0),
                'submitted',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND lower(d.status) = 'pending_validation'
                ), 0),
                'planned',
                COALESCE((
                    SELECT COUNT(*)
                    FROM documents d
                    WHERE d.candidate_id = {candidate_id}
                      AND d.deleted_at IS NULL
                      AND lower(d.status) = 'planned'
                ), 0)
            )
        """

        op.execute(
            f"""
            CREATE TRIGGER trg_docs_after_insert
            AFTER INSERT ON documents
            BEGIN
                UPDATE candidates
                SET docs_progress = {docs_progress_sql.format(candidate_id='NEW.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.candidate_id;
            END;
            """
        )

        op.execute(
            f"""
            CREATE TRIGGER trg_docs_after_update
            AFTER UPDATE OF status, files, filename, deleted_at, candidate_id ON documents
            BEGIN
                UPDATE candidates
                SET docs_progress = {docs_progress_sql.format(candidate_id='NEW.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.candidate_id;

                UPDATE candidates
                SET docs_progress = {docs_progress_sql.format(candidate_id='OLD.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.candidate_id AND OLD.candidate_id IS NOT NEW.candidate_id;
            END;
            """
        )

        op.execute(
            f"""
            CREATE TRIGGER trg_docs_after_delete
            AFTER DELETE ON documents
            BEGIN
                UPDATE candidates
                SET docs_progress = {docs_progress_sql.format(candidate_id='OLD.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.candidate_id;
            END;
            """
        )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    is_sqlite = dialect == "sqlite"

    # drop helper indexes before recreating the table
    for idx in (
        "ix_documents_expires_at",
        "ix_documents_status",
        "ix_documents_tenant_candidate_type",
        "ix_documents_type",
    ):
        try:
            op.drop_index(idx, table_name="documents")
        except Exception:
            pass

    # best-effort downgrade: drop new columns and restore defaults
    with op.batch_alter_table("documents", recreate="always") as batch:
        for column in ("verified_at", "external_id", "source", "files", "number"):
            if _has_column("documents", column):
                batch.drop_column(column)

        if not _has_column("documents", "key") and _has_column("documents", "type"):
            batch.alter_column(
                "type",
                new_column_name="key",
                existing_type=sa.String(length=100),
                nullable=False,
            )

        batch.alter_column(
            "status",
            existing_type=sa.String(length=50),
            nullable=True,
            server_default=sa.text("'uploaded'"),
        )
        batch.alter_column(
            "reminder_days_before",
            existing_type=sa.Integer(),
            nullable=True,
            server_default=None,
        )

        # legacy duplicates (issued/expires_date) cannot be recreated automatically

    # recreate legacy indexes referencing the original column name
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_key ON documents (key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_tenant_candidate_key ON documents (tenant_id, candidate_id, key)")

    if is_sqlite:
        # restore previous trigger logic (basic counters)
        for trig in (
            "trg_docs_after_insert",
            "trg_docs_after_update",
            "trg_docs_after_delete",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS {trig}")

        legacy_progress_sql = """
            json_object(
                'total', COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = {candidate_id} AND d.deleted_at IS NULL), 0),
                'uploaded', COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = {candidate_id} AND d.deleted_at IS NULL AND d.filename IS NOT NULL AND length(trim(d.filename)) > 0), 0),
                'ready', COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = {candidate_id} AND d.deleted_at IS NULL AND lower(d.status) = 'ready'), 0),
                'submitted', COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = {candidate_id} AND d.deleted_at IS NULL AND lower(d.status) = 'submitted'), 0),
                'planned', COALESCE((SELECT COUNT(*) FROM documents d WHERE d.candidate_id = {candidate_id} AND d.deleted_at IS NULL AND lower(d.status) = 'planned'), 0)
            )
        """

        op.execute(
            f"""
            CREATE TRIGGER trg_docs_after_insert
            AFTER INSERT ON documents
            BEGIN
                UPDATE candidates
                SET docs_progress = {legacy_progress_sql.format(candidate_id='NEW.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.candidate_id;
            END;
            """
        )

        op.execute(
            f"""
            CREATE TRIGGER trg_docs_after_update
            AFTER UPDATE OF status, filename, deleted_at, candidate_id ON documents
            BEGIN
                UPDATE candidates
                SET docs_progress = {legacy_progress_sql.format(candidate_id='NEW.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.candidate_id;

                UPDATE candidates
                SET docs_progress = {legacy_progress_sql.format(candidate_id='OLD.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.candidate_id AND OLD.candidate_id IS NOT NEW.candidate_id;
            END;
            """
        )

        op.execute(
            f"""
            CREATE TRIGGER trg_docs_after_delete
            AFTER DELETE ON documents
            BEGIN
                UPDATE candidates
                SET docs_progress = {legacy_progress_sql.format(candidate_id='OLD.candidate_id')},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.candidate_id;
            END;
            """
        )
