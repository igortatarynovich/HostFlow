"""Ensure magic_links.meta exists (compat with DBs created before full magic_links migration).

Revision ID: 202604021502_ml_meta
Revises: 202604021500_intake_tenant
Create Date: 2026-04-02
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "202604021502_ml_meta"
down_revision: Union[str, None] = "202604021500_intake_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        """
        DO $hf$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'magic_links'
          ) AND NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'magic_links' AND column_name = 'meta'
          ) THEN
            ALTER TABLE public.magic_links ADD COLUMN meta JSONB;
          END IF;
        END
        $hf$;
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE public.magic_links DROP COLUMN IF EXISTS meta")
