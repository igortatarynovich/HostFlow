"""Introduce recruiter assignment support.

- Adds vacancy_recruiters mapping table with weights and rotation metadata.
- Extends candidates with recruiter_id reference.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202512010300_recruiter_assignment"
down_revision = "202512010200_admin_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vacancy_recruiters",
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("vacancy_id", "user_id", name="pk_vacancy_recruiters"),
    )
    op.create_index(
        "ix_vacancy_recruiters_tenant",
        "vacancy_recruiters",
        ["tenant_id"],
    )
    op.create_index(
        "ix_vacancy_recruiters_vacancy",
        "vacancy_recruiters",
        ["vacancy_id"],
    )

    op.add_column(
        "candidates",
        sa.Column("recruiter_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_candidates_recruiter_id",
        "candidates",
        ["recruiter_id"],
    )
    op.create_foreign_key(
        "fk_candidates_recruiter_id_users",
        "candidates",
        "users",
        ["recruiter_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_candidates_recruiter_id_users",
        "candidates",
        type_="foreignkey",
    )
    op.drop_index("ix_candidates_recruiter_id", table_name="candidates")
    op.drop_column("candidates", "recruiter_id")

    op.drop_index("ix_vacancy_recruiters_vacancy", table_name="vacancy_recruiters")
    op.drop_index("ix_vacancy_recruiters_tenant", table_name="vacancy_recruiters")
    op.drop_table("vacancy_recruiters")
