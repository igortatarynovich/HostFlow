"""Add contract lifecycle fields to workforce_employments.

Revision ID: 202605250003_workforce_contract_lifecycle_fields
Revises: 202608130005_merge_m5_heads
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202605250003_workforce_contract_lifecycle_fields"
down_revision = "202608130005_merge_m5_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workforce_employments", sa.Column("lifecycle_status", sa.String(length=32), nullable=True))
    op.add_column("workforce_employments", sa.Column("employer_name", sa.String(length=160), nullable=True))
    op.add_column("workforce_employments", sa.Column("probation_end", sa.Date(), nullable=True))
    op.add_column("workforce_employments", sa.Column("signed_at", sa.Date(), nullable=True))
    op.add_column("workforce_employments", sa.Column("latest_annex_ref", sa.String(length=160), nullable=True))
    op.add_column("workforce_employments", sa.Column("expiry_date", sa.Date(), nullable=True))
    op.add_column("workforce_employments", sa.Column("next_action", sa.String(length=256), nullable=True))

    op.execute("UPDATE workforce_employments SET lifecycle_status = 'issued' WHERE lifecycle_status IS NULL OR lifecycle_status = ''")
    op.execute("UPDATE workforce_employments SET expiry_date = end_date WHERE expiry_date IS NULL AND end_date IS NOT NULL")

    op.alter_column("workforce_employments", "lifecycle_status", existing_type=sa.String(length=32), nullable=False)


def downgrade() -> None:
    op.drop_column("workforce_employments", "next_action")
    op.drop_column("workforce_employments", "expiry_date")
    op.drop_column("workforce_employments", "latest_annex_ref")
    op.drop_column("workforce_employments", "signed_at")
    op.drop_column("workforce_employments", "probation_end")
    op.drop_column("workforce_employments", "employer_name")
    op.drop_column("workforce_employments", "lifecycle_status")
