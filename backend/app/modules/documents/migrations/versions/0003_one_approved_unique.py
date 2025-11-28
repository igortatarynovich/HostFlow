"""unique approved per owner/type (partial index)

Revision ID: 0003_one_approved_unique
Revises: 0002_seed_types_ruleset
Create Date: 2025-09-07
"""

from __future__ import annotations

from alembic import op

# revision identifiers
revision = "0003_one_approved_unique"
down_revision = "0002_seed_types_ruleset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_docs_one_approved
        ON documents(tenant_id, owner_type, owner_id, type_id)
        WHERE status = 'approved';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_docs_one_approved;")
