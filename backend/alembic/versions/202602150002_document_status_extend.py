"""Extend document status enum with workflow states

Revision ID: 202602150002
Revises: 202602150001
Create Date: 2025-11-02 17:05:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "202602150002"
down_revision = "202602150001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE document_status_enum_v2 ADD VALUE IF NOT EXISTS 'submitted'")
    op.execute("ALTER TYPE document_status_enum_v2 ADD VALUE IF NOT EXISTS 'delivered'")
    op.execute("ALTER TYPE document_status_enum_v2 ADD VALUE IF NOT EXISTS 'completed'")
    op.execute("ALTER TYPE document_status_enum_v2 ADD VALUE IF NOT EXISTS 'overdue'")


def downgrade() -> None:
    # Enum values cannot be dropped safely; leave as-is.
    pass
