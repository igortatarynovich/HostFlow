"""Allow clients to see candidates in handoffs (RLS policy for Do procesowania)

When a client tenant (e.g. Citronex) queries handoffs with client_tenant_id,
the join with candidates was filtered by RLS (candidate.tenant_id = app.tenant_id).
Candidates belong to the agency tenant, so the client saw no rows.

This migration adds an RLS policy allowing read access to candidates when
there exists a handoff with client_tenant_id = current tenant.

Revision ID: 202608080001
Revises: 202608060002_backfill_latin
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202608080001"
down_revision: Union[str, None] = "202608060002_backfill_latin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    # Add policy: allow reading candidates when there's a handoff to current tenant
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = current_schema()
                  AND tablename = 'candidates'
                  AND policyname = 'rls_candidates_handoff_client'
            ) THEN
                CREATE POLICY rls_candidates_handoff_client ON candidates
                USING (
                    tenant_id::uuid = current_setting('app.tenant_id')::uuid
                    OR EXISTS (
                        SELECT 1 FROM candidate_handoffs h
                        WHERE h.candidate_id = candidates.id
                        AND h.client_tenant_id IS NOT NULL
                        AND h.client_tenant_id::uuid = current_setting('app.tenant_id')::uuid
                    )
                );
            END IF;
        END $$;
    """)


def downgrade() -> None:
    if not _is_postgres():
        return

    op.execute("""
        DROP POLICY IF EXISTS rls_candidates_handoff_client ON candidates;
    """)
