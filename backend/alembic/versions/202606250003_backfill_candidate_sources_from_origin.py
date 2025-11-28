"""Backfill candidate sources based on origin JSON.

Revision ID: 202606250003_backfill_candidate_sources_from_origin
Revises: 202606250002_normalize_candidate_sources
Create Date: 2025-06-25 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606250003_backfill_candidate_sources_from_origin"
down_revision = "202606250002_normalize_candidate_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    fb_keys = (
        "'meta','facebook','facebook_ads','facebookads','fb','fb_ads'"
    )
    form_keys = (
        "'public-intake','public-intake-ui','public_intake','public_intake_ui','public-form','public_form','website_form','site_form','form'"
    )
    conn.execute(
        sa.text(
            f"""
            UPDATE candidates
            SET source = 'FB'
            WHERE (source IS NULL OR source = '')
              AND origin IS NOT NULL
              AND (
                lower(COALESCE((origin::jsonb ->> 'source'),''))
                  IN ({fb_keys})
                OR EXISTS (
                    SELECT 1
                    FROM jsonb_object_keys(origin::jsonb) AS k
                    WHERE lower(k) IN ({fb_keys})
                )
              )
            """
        )
    )
    conn.execute(
        sa.text(
            f"""
            UPDATE candidates
            SET source = 'Анкета'
            WHERE (source IS NULL OR source = '')
              AND origin IS NOT NULL
              AND (
                lower(COALESCE((origin::jsonb ->> 'source'),''))
                  IN ({form_keys})
                OR EXISTS (
                    SELECT 1
                    FROM jsonb_object_keys(origin::jsonb) AS k
                    WHERE lower(k) IN ({form_keys})
                )
              )
            """
        )
    )


def downgrade() -> None:
    # Nothing to undo safely (source was previously empty)
    pass

