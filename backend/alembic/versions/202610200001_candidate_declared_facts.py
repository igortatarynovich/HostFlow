"""Declared intake facts and trailer hiring mappings.

Revision ID: 202610200001_candidate_declared_facts
Revises: 202610160001_professional_profile_schema

Does not rewrite legacy experience scalars and does not create employments.
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "202610200001_candidate_declared_facts"
down_revision: Union[str, None] = "202610160001_professional_profile_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_HIRING = ("curtain", "reefer", "container", "tanker", "dump", "platform")
_ALIASES = (("tent", "curtain"), ("frigo", "reefer"))


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _rls_tenant(table: str) -> None:
    if not _is_postgres():
        return
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = '{table}'
                AND policyname = 'rls_{table}_tenant'
            ) THEN
                CREATE POLICY rls_{table}_tenant ON {table}
                USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    uid = sa.String(36)
    op.create_table(
        "candidate_declared_facts",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", uid, sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(32), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("years", sa.Numeric(8, 4), nullable=True),
        sa.Column("presence", sa.Boolean(), nullable=True),
        sa.Column("provenance", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tenant_id", "candidate_id", "subject", "code", name="uq_candidate_declared_facts_scope"),
    )
    op.create_index("ix_candidate_declared_facts_tenant_id", "candidate_declared_facts", ["tenant_id"])
    op.create_index("ix_candidate_declared_facts_candidate_id", "candidate_declared_facts", ["candidate_id"])
    _rls_tenant("candidate_declared_facts")

    rows = []
    for code in _HIRING:
        for vocabulary in ("trailer_intake", "trailer_employment_raw"):
            rows.append(
                {
                    "id": str(uuid4()),
                    "source_vocabulary": vocabulary,
                    "source_code": code,
                    "target_vocabulary": "trailer_hiring",
                    "target_code": code,
                }
            )
    for source_code, target_code in _ALIASES:
        for vocabulary in ("trailer_intake", "trailer_employment_raw"):
            rows.append(
                {
                    "id": str(uuid4()),
                    "source_vocabulary": vocabulary,
                    "source_code": source_code,
                    "target_vocabulary": "trailer_hiring",
                    "target_code": target_code,
                }
            )
    op.bulk_insert(sa.table(
        "professional_code_mappings",
        sa.column("id", uid),
        sa.column("source_vocabulary", sa.String(64)),
        sa.column("source_code", sa.String(64)),
        sa.column("target_vocabulary", sa.String(64)),
        sa.column("target_code", sa.String(64)),
    ), rows)


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM professional_code_mappings
        WHERE target_vocabulary = 'trailer_hiring'
          AND source_vocabulary IN ('trailer_intake', 'trailer_employment_raw')
        """
    )
    op.drop_index("ix_candidate_declared_facts_candidate_id", table_name="candidate_declared_facts")
    op.drop_index("ix_candidate_declared_facts_tenant_id", table_name="candidate_declared_facts")
    op.drop_table("candidate_declared_facts")
