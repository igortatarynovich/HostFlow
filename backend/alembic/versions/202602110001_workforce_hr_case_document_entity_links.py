"""workforce_hr_cases + document_entity_links (HR operational context / ADR-009 link MVP)

Revision ID: 202602110001_hr_ctx_links
Revises: 202605090001_tint_ce

Data safety (upgrade):
  - Additive only: creates empty tables if missing. No ALTER/DROP/TRUNCATE on existing
    application tables (including `documents`, `document_files`, candidates, workforce).
  - Does not copy or move file blobs; rows in `document_entity_links` only reference
    existing `documents.id` (FK). Deleting a document later is app-level behavior, not
    introduced by this migration.

Downgrade:
  - Drops `document_entity_links` and `workforce_hr_cases` only. Does NOT delete
    documents or files. HR case / reuse metadata is lost if you downgrade.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202602110001_hr_ctx_links"
down_revision: Union[str, None] = "202605090001_tint_ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    bind = op.get_bind()
    jt = postgresql.JSONB(astext_type=sa.Text()) if _is_pg() else sa.JSON()
    ts = sa.DateTime(timezone=True)
    uid = sa.String(36)

    insp = sa.inspect(bind)
    if not insp.has_table("workforce_hr_cases"):
        op.create_table(
            "workforce_hr_cases",
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column(
                "tenant_id",
                uid,
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "employee_id",
                uid,
                sa.ForeignKey("workforce_employees.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "source_candidate_id",
                uid,
                sa.ForeignKey("candidates.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("status", sa.String(32), nullable=False, server_default="open"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("meta", jt, nullable=True),
            sa.Column("created_at", ts, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", ts, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.UniqueConstraint("tenant_id", "employee_id", name="uq_workforce_hr_case_tenant_employee"),
        )

    insp = sa.inspect(bind)
    if not insp.has_table("document_entity_links"):
        op.create_table(
            "document_entity_links",
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column(
                "tenant_id",
                uid,
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "document_id",
                uid,
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("linked_entity_type", sa.String(64), nullable=False),
            sa.Column("linked_entity_id", uid, nullable=False, index=True),
            sa.Column("relation_type", sa.String(64), nullable=False),
            sa.Column("module_key", sa.String(32), nullable=True),
            sa.Column("created_at", ts, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.UniqueConstraint(
                "tenant_id",
                "document_id",
                "linked_entity_type",
                "linked_entity_id",
                "relation_type",
                name="uq_document_entity_link_scope",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("document_entity_links"):
        op.drop_table("document_entity_links")
    if insp.has_table("workforce_hr_cases"):
        op.drop_table("workforce_hr_cases")
