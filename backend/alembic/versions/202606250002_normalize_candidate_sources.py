"""Normalize candidate source labels to FB/Анкета.

Revision ID: 202606250002_normalize_candidate_sources
Revises: 202606250001_candidate_consents_log
Create Date: 2025-06-25 11:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606250002_normalize_candidate_sources"
down_revision = "202606250001_candidate_consents_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    fb_keys = [
        "meta",
        "facebook",
        "facebook_ads",
        "facebookads",
        "fb",
        "fb_ads",
    ]
    form_keys = [
        "public-intake",
        "public_intake",
        "public-form",
        "public_form",
        "website_form",
        "site_form",
        "form",
    ]
    for key in fb_keys:
        conn.execute(
            sa.text("UPDATE candidates SET source = 'FB' WHERE lower(source) = :key"),
            {"key": key},
        )
    for key in form_keys:
        conn.execute(
            sa.text("UPDATE candidates SET source = 'Анкета' WHERE lower(source) = :key"),
            {"key": key},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE candidates SET source = 'meta' WHERE source = 'FB'"))
    conn.execute(sa.text("UPDATE candidates SET source = 'public-intake' WHERE source = 'Анкета'"))

