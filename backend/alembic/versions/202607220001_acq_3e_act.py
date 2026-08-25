"""Stage 3E PR-1: Acquisition Activity Timeline foundation.

Revision ID: 202607220001_acq_3e_act
Revises: 202607210002_comm_automation_domain_c2_2
Create Date: 2026-07-21

NOTE: revision id kept ≤32 chars.
Chains from Communication C2.2 tip on integration (C2.3 is Engineering Track).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607220001_acq_3e_act"
down_revision: RevisionType = "202607210002_comm_automation_domain_c2_2"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "acquisition_activity_events" in insp.get_table_names():
        return

    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "acquisition_activity_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("flight_id", sa.String(length=36), nullable=True),
        sa.Column("endpoint_id", sa.String(length=64), nullable=True),
        sa.Column("submission_id", sa.String(length=36), nullable=True),
        sa.Column("result_id", sa.String(length=64), nullable=True),
        sa.Column("outcome_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_version", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("source_event_id", sa.String(length=191), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("causation_id", sa.String(length=64), nullable=True),
        sa.Column("payload", json_type, nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["acq_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["flight_id"],
            ["acq_campaign_runs.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_acquisition_activity_events_tenant_id",
        "acquisition_activity_events",
        ["tenant_id"],
    )
    op.create_index(
        "ix_acquisition_activity_events_campaign_id",
        "acquisition_activity_events",
        ["campaign_id"],
    )
    op.create_index(
        "ix_acquisition_activity_events_flight_id",
        "acquisition_activity_events",
        ["flight_id"],
    )
    op.create_index(
        "ix_acquisition_activity_events_outcome_id",
        "acquisition_activity_events",
        ["outcome_id"],
    )
    op.create_index(
        "ix_acq_act_ev_tenant_campaign_occurred",
        "acquisition_activity_events",
        ["tenant_id", "campaign_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_acq_act_ev_tenant_flight_occurred",
        "acquisition_activity_events",
        ["tenant_id", "flight_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_acq_act_ev_tenant_submission_occurred",
        "acquisition_activity_events",
        ["tenant_id", "submission_id", "occurred_at"],
    )
    op.create_index(
        "ix_acq_act_ev_tenant_type_occurred",
        "acquisition_activity_events",
        ["tenant_id", "event_type", "occurred_at"],
    )

    # Tenant-scoped idempotency (NULL source_event_id allowed many times).
    if dialect == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX uq_acq_act_ev_tenant_source_event
            ON acquisition_activity_events (tenant_id, source_event_id)
            WHERE source_event_id IS NOT NULL
            """
        )
        op.execute("ALTER TABLE acquisition_activity_events ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'acquisition_activity_events'
                  AND policyname = 'tenant_isolation'
              ) THEN
                CREATE POLICY tenant_isolation ON acquisition_activity_events
                  USING (tenant_id = current_setting('app.tenant_id', true))
                  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
              END IF;
            END $$;
            """
        )
        # Hard immutability: block ANY UPDATE (all columns) and DELETE of event rows.
        op.execute(
            """
            CREATE OR REPLACE FUNCTION acquisition_activity_events_immutable()
            RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION
                'acquisition_activity_events is append-only '
                '(no UPDATE of any column, no DELETE)';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            DROP TRIGGER IF EXISTS trg_acquisition_activity_events_immutable
              ON acquisition_activity_events
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_acquisition_activity_events_immutable
              BEFORE UPDATE OR DELETE ON acquisition_activity_events
              FOR EACH ROW
              EXECUTE FUNCTION acquisition_activity_events_immutable()
            """
        )
    else:
        op.create_index(
            "uq_acq_act_ev_tenant_source_event",
            "acquisition_activity_events",
            ["tenant_id", "source_event_id"],
            unique=True,
            sqlite_where=sa.text("source_event_id IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "acquisition_activity_events" not in insp.get_table_names():
        return

    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_acquisition_activity_events_immutable "
            "ON acquisition_activity_events"
        )
        op.execute("DROP FUNCTION IF EXISTS acquisition_activity_events_immutable()")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON acquisition_activity_events")
        op.execute("ALTER TABLE acquisition_activity_events DISABLE ROW LEVEL SECURITY")

    op.drop_table("acquisition_activity_events")
