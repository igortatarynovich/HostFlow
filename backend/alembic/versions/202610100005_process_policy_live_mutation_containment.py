"""contain deliberately-live Process Profile policy mutation

Revision ID: 202610100005_process_policy_live_mutation_containment
Revises: 202610100004_entity_profile_process_profile_composition
"""

from alembic import op
import sqlalchemy as sa


revision = "202610100005_process_policy_live_mutation_containment"
down_revision = "202610100004_entity_profile_process_profile_composition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pe_process_profiles",
        sa.Column(
            "policy_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Optimistic concurrency revision for controlled live policy corrections",
        ),
    )

    op.drop_constraint(
        "fk_vacancies_pe_process_profile_id",
        "vacancies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_vacancies_pe_process_profile_id",
        "vacancies",
        "pe_process_profiles",
        ["pe_process_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_candidate_profiles_pe_process_profile_id",
        "candidate_profiles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_candidate_profiles_pe_process_profile_id",
        "candidate_profiles",
        "pe_process_profiles",
        ["pe_process_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_candidate_profiles_pe_process_profile_id",
        "candidate_profiles",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_candidate_profiles_pe_process_profile_id",
        "candidate_profiles",
        "pe_process_profiles",
        ["pe_process_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "fk_vacancies_pe_process_profile_id",
        "vacancies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_vacancies_pe_process_profile_id",
        "vacancies",
        "pe_process_profiles",
        ["pe_process_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_column("pe_process_profiles", "policy_revision")
