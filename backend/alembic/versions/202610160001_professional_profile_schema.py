"""Professional profile schema: employment facets, constraints, preferences, timezone.

Revision ID: 202610160001_professional_profile_schema
Revises: 202610100006_process_profile_rule_uniqueness

No experience values are rewritten. New employment lists start empty.
Existing tenants receive Europe/Warsaw as a data backfill. The column has
no server default.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202610160001_professional_profile_schema"
down_revision: Union[str, None] = "202610100006_process_profile_rule_uniqueness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _json_type() -> sa.types.TypeEngine:
    if _is_postgres():
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default() -> sa.sql.elements.TextClause:
    if _is_postgres():
        return sa.text("'[]'::jsonb")
    return sa.text("'[]'")


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
    json_type = _json_type()
    json_default = _json_default()
    uid = sa.String(36)
    for column in (
        "driving_categories",
        "operation_scopes",
        "movement_patterns",
        "crew_modes",
        "work_areas",
    ):
        op.add_column(
            "candidate_employments",
            sa.Column(column, json_type, nullable=False, server_default=json_default),
        )

    op.create_table(
        "professional_catalog_codes",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, nullable=False, server_default=""),
        sa.Column("vocabulary", sa.String(64), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tenant_id", "vocabulary", "code", name="uq_professional_catalog_codes_scope"),
    )
    op.create_index("ix_professional_catalog_codes_tenant_id", "professional_catalog_codes", ["tenant_id"])

    from backend.app.reference.professional_profile_catalogs import catalog_code_pairs
    from uuid import uuid4

    op.bulk_insert(
        sa.table(
            "professional_catalog_codes",
            sa.column("id", uid),
            sa.column("tenant_id", uid),
            sa.column("vocabulary", sa.String),
            sa.column("code", sa.String),
        ),
        [
            {"id": str(uuid4()), "tenant_id": "", "vocabulary": vocabulary, "code": code}
            for vocabulary, code in catalog_code_pairs()
        ],
    )

    op.create_table(
        "professional_code_mappings",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("source_vocabulary", sa.String(64), nullable=False),
        sa.Column("source_code", sa.String(64), nullable=False),
        sa.Column("target_vocabulary", sa.String(64), nullable=False),
        sa.Column("target_code", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint(
            "source_vocabulary",
            "source_code",
            "target_vocabulary",
            name="uq_professional_code_mappings_source",
        ),
    )

    def candidate_table(name: str, columns: list[sa.Column], unique: sa.UniqueConstraint | None = None) -> None:
        args: list = [
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("candidate_id", uid, sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
            *columns,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        ]
        if unique is not None:
            args.append(unique)
        op.create_table(name, *args)
        op.create_index(f"ix_{name}_tenant_id", name, ["tenant_id"])
        op.create_index(f"ix_{name}_candidate_id", name, ["candidate_id"])
        _rls_tenant(name)

    candidate_table(
        "candidate_professional_constraints",
        [
            sa.Column("subject", sa.String(32), nullable=False),
            sa.Column("code", sa.String(64), nullable=False),
            sa.Column("effect", sa.String(16), nullable=False),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
        ],
    )
    candidate_table(
        "candidate_availability",
        [sa.Column("available_from", sa.Date(), nullable=True)],
        sa.UniqueConstraint("tenant_id", "candidate_id", name="uq_candidate_availability_candidate"),
    )
    candidate_table(
        "candidate_preference_choices",
        [
            sa.Column("subject", sa.String(32), nullable=False),
            sa.Column("kind", sa.String(16), nullable=True),
            sa.Column("code", sa.String(64), nullable=False),
        ],
    )
    candidate_table(
        "candidate_compensation_expectations",
        [
            sa.Column("amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("currency", sa.String(3), nullable=True),
            sa.Column("period", sa.String(32), nullable=True),
        ],
        sa.UniqueConstraint("tenant_id", "candidate_id", name="uq_candidate_compensation_candidate"),
    )

    op.add_column("tenants", sa.Column("timezone", sa.String(64), nullable=True))
    op.execute("UPDATE tenants SET timezone = 'Europe/Warsaw' WHERE timezone IS NULL")
    op.alter_column("tenants", "timezone", existing_type=sa.String(64), nullable=False)


def downgrade() -> None:
    op.drop_column("tenants", "timezone")
    for name in (
        "candidate_compensation_expectations",
        "candidate_preference_choices",
        "candidate_availability",
        "candidate_professional_constraints",
        "professional_code_mappings",
        "professional_catalog_codes",
    ):
        op.drop_table(name)
    for column in (
        "work_areas",
        "crew_modes",
        "movement_patterns",
        "operation_scopes",
        "driving_categories",
    ):
        op.drop_column("candidate_employments", column)
