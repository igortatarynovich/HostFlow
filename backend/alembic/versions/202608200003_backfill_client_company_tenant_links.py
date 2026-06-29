"""Backfill tenant_links for agency client companies created via CRM directory.

Revision ID: 202608200003
Revises: 202608200002_intake_source_profiles_public_link
Create Date: 2026-06-17

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "202608200003"
down_revision: Union[str, None] = "202608200002_intake_source_profiles_public_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO tenant_links (
            id,
            agency_tenant_id,
            client_company_id,
            client_tenant_id,
            handoff_include_company_id,
            status,
            features_json,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid()::text,
            c.tenant_id,
            c.id,
            NULL,
            NULL,
            'active',
            '{"handoff_enabled": false}'::jsonb,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM companies c
        JOIN tenants t ON t.id = c.tenant_id AND t.type = 'agency'
        WHERE LOWER(COALESCE(c.extra::jsonb->>'company_role', '')) = 'client'
          AND NOT EXISTS (
              SELECT 1
              FROM tenant_links tl
              WHERE tl.agency_tenant_id = c.tenant_id
                AND tl.client_company_id = c.id
          )
        """
    )


def downgrade() -> None:
    pass
