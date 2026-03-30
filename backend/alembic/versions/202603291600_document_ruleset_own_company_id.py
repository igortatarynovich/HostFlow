"""document_ruleset_versions.own_company_id for §2.4 scoped rulesets

Revision ID: 202603291600_doc_ruleset_oc
Revises: 202603291500_doc_pol_oc
Create Date: 2026-03-29

Replaces single (tenant_id, version) uniqueness with partial unique indexes:
- global chain: own_company_id IS NULL
- per–own-company chain: own_company_id NOT NULL

Note: Do not use bare try/except around failing SQL inside Alembic's transaction —
PostgreSQL aborts the transaction on error; catching the exception leaves the
connection unusable (InFailedSqlTransaction). Use IF EXISTS / IF NOT EXISTS only.

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202603291600_doc_ruleset_oc"
down_revision: Union[str, None] = "202603291500_doc_pol_oc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def _has_column(conn: sa.Connection, table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(conn).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "document_ruleset_versions"):
        return

    if not _has_column(conn, "document_ruleset_versions", "own_company_id"):
        with op.batch_alter_table("document_ruleset_versions", schema=None) as batch_op:
            batch_op.add_column(sa.Column("own_company_id", sa.String(length=36), nullable=True))

    # Non-unique helper index — never fail the migration if it already exists
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_document_ruleset_versions_own_company_id "
            "ON document_ruleset_versions (own_company_id)"
        )
    )

    # Drop legacy uniqueness (constraint owns the backing index on PostgreSQL).
    # Do NOT use op.drop_index() here: it errors ("constraint requires it") and aborts the txn.
    op.execute(
        sa.text(
            "ALTER TABLE document_ruleset_versions "
            "DROP CONSTRAINT IF EXISTS uq_document_ruleset_versions_tenant_version"
        )
    )
    op.execute(
        sa.text(
            "DROP INDEX IF EXISTS uq_document_ruleset_versions_tenant_version"
        )
    )

    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_global_version "
            "ON document_ruleset_versions (tenant_id, version) "
            "WHERE own_company_id IS NULL"
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_scoped_version "
            "ON document_ruleset_versions (tenant_id, own_company_id, version) "
            "WHERE own_company_id IS NOT NULL"
        )
    )

    if sa.inspect(conn).has_table("own_companies"):
        op.execute(
            sa.text(
                """
                DO $bd$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_document_ruleset_versions_own_company_id'
                  ) THEN
                    ALTER TABLE document_ruleset_versions
                      ADD CONSTRAINT fk_document_ruleset_versions_own_company_id
                      FOREIGN KEY (own_company_id) REFERENCES own_companies(id)
                      ON DELETE SET NULL;
                  END IF;
                END $bd$;
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "document_ruleset_versions"):
        return

    op.execute(
        sa.text(
            "ALTER TABLE document_ruleset_versions "
            "DROP CONSTRAINT IF EXISTS fk_document_ruleset_versions_own_company_id"
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS uq_document_ruleset_scoped_version"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_document_ruleset_global_version"))

    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_versions_tenant_version "
            "ON document_ruleset_versions (tenant_id, version)"
        )
    )

    if _has_column(conn, "document_ruleset_versions", "own_company_id"):
        op.execute(
            sa.text("DROP INDEX IF EXISTS ix_document_ruleset_versions_own_company_id")
        )
        with op.batch_alter_table("document_ruleset_versions", schema=None) as batch_op:
            batch_op.drop_column("own_company_id")
