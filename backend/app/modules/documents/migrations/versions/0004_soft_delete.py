"""soft delete for documents + fix unique index to ignore deleted

Revision ID: 0004_soft_delete
Revises: 0003_one_approved_unique
Create Date: 2025-09-07
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_soft_delete"
down_revision = "0003_one_approved_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) add deleted_at column
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;"
    )

    # 2) recreate unique index to ignore deleted rows
    op.execute("DROP INDEX IF EXISTS uq_docs_one_approved;")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_docs_one_approved
        ON documents(tenant_id, owner_type, owner_id, type_id)
        WHERE status = 'approved' AND deleted_at IS NULL;
        """
    )

    # 3) helper index for typical filters (only non-deleted)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_documents_owner_active
        ON documents(tenant_id, owner_type, owner_id)
        WHERE deleted_at IS NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_owner_active;")
    op.execute("DROP INDEX IF EXISTS uq_docs_one_approved;")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_docs_one_approved
        ON documents(tenant_id, owner_type, owner_id, type_id)
        WHERE status = 'approved';
        """
    )
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS deleted_at;")
