"""scope transition-rule uniqueness to owning Process Profile

Revision ID: 202610100006_process_profile_rule_uniqueness
Revises: 202610100005_process_policy_live_mutation_containment
"""

import sqlalchemy as sa
from alembic import op


revision = "202610100006_process_profile_rule_uniqueness"
down_revision = "202610100005_process_policy_live_mutation_containment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_pe_transition_rules_scope_code",
        "pe_transition_rules",
        type_="unique",
    )
    op.create_index(
        "uq_pe_transition_rules_owned_scope_code",
        "pe_transition_rules",
        ["tenant_id", "module", "process_profile_id", "code"],
        unique=True,
        postgresql_where=sa.text("process_profile_id IS NOT NULL"),
    )
    op.create_index(
        "uq_pe_transition_rules_unowned_scope_code",
        "pe_transition_rules",
        ["tenant_id", "module", "code"],
        unique=True,
        postgresql_where=sa.text("process_profile_id IS NULL"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    duplicate = bind.execute(
        sa.text(
            """
            SELECT tenant_id, module, code, count(*) AS row_count
            FROM pe_transition_rules
            GROUP BY tenant_id, module, code
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).mappings().first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot restore global transition-rule uniqueness: duplicate "
            f"tenant/module/code exists ({duplicate['tenant_id']!r}, "
            f"{duplicate['module']!r}, {duplicate['code']!r}); "
            "remove or migrate incompatible cloned policy data before downgrade"
        )

    op.drop_index(
        "uq_pe_transition_rules_unowned_scope_code",
        table_name="pe_transition_rules",
    )
    op.drop_index(
        "uq_pe_transition_rules_owned_scope_code",
        table_name="pe_transition_rules",
    )
    op.create_unique_constraint(
        "uq_pe_transition_rules_scope_code",
        "pe_transition_rules",
        ["tenant_id", "module", "code"],
    )
