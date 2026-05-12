"""Document dossier zones (recruitment / internal_hr / client) and per-user shares.

Revision ID: 202605060001_document_dossier_zones
Revises: 202604302532_fleet_assignments_legacy_driver
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605060001_document_dossier_zones"
down_revision: Union[str, None] = "202604302532_fleet_assignments_legacy_driver"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "documents", "dossier_zone"):
        op.add_column(
            "documents",
            sa.Column(
                "dossier_zone",
                sa.String(32),
                nullable=False,
                server_default="recruitment",
            ),
        )

    if not _has_table(bind, "document_dossier_shares"):
        op.create_table(
            "document_dossier_shares",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
            sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("grantee_user_id", sa.String(36), nullable=False, index=True),
            sa.Column("granted_by_user_id", sa.String(36), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
        op.create_index(
            "ix_document_dossier_shares_document_id",
            "document_dossier_shares",
            ["document_id"],
            unique=False,
        )
        op.create_index(
            "ix_document_dossier_shares_tenant_grantee",
            "document_dossier_shares",
            ["tenant_id", "grantee_user_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "document_dossier_shares"):
        op.drop_index("ix_document_dossier_shares_tenant_grantee", table_name="document_dossier_shares")
        op.drop_index("ix_document_dossier_shares_document_id", table_name="document_dossier_shares")
        op.drop_table("document_dossier_shares")
    if _has_column(bind, "documents", "dossier_zone"):
        op.drop_column("documents", "dossier_zone")
