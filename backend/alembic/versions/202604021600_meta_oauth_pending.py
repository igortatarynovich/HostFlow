"""meta_oauth_pending: Meta Leads Facebook Login OAuth (pending page tokens).

Revision ID: 202604021600_meta_oauth_p
Revises: 202604021502_ml_meta
Create Date: 2026-04-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604021600_meta_oauth_p"
down_revision: Union[str, None] = "202604021502_ml_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.create_table(
        "meta_oauth_pending",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meta_oauth_pending_tenant_id", "meta_oauth_pending", ["tenant_id"], unique=False)
    op.create_index("ix_meta_oauth_pending_expires_at", "meta_oauth_pending", ["expires_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_meta_oauth_pending_expires_at", table_name="meta_oauth_pending")
    op.drop_index("ix_meta_oauth_pending_tenant_id", table_name="meta_oauth_pending")
    op.drop_table("meta_oauth_pending")
