"""202607180008_forms_s3 — append-only form publication version ledger.

Revision ID: 202607180008_forms_s3
Revises: 202607180007_forms_s2
Create Date: 2026-07-18

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180008_forms_s3"
down_revision: RevisionType = "202607180007_forms_s2"
branch_labels: RevisionType = None
depends_on: RevisionType = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "form_publication_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("form_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", _JSON, nullable=False),
        sa.Column("consent_pin", _JSON, nullable=False),
        sa.Column("submission_pin_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["form_id"], ["tenant_lead_forms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "form_id", "version", name="uq_form_pub_versions_tenant_form_ver"
        ),
    )
    op.create_index(
        "ix_form_pub_versions_tenant_form",
        "form_publication_versions",
        ["tenant_id", "form_id"],
    )
    op.create_index(
        "ix_form_pub_versions_tenant_id",
        "form_publication_versions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_form_pub_versions_form_id",
        "form_publication_versions",
        ["form_id"],
    )
    # Partial unique for idempotency (Postgres); sqlite accepts WHERE on unique index in 3.8+.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX ix_form_pub_versions_idem "
                "ON form_publication_versions (tenant_id, form_id, idempotency_key) "
                "WHERE idempotency_key IS NOT NULL"
            )
        )
    else:
        op.create_index(
            "ix_form_pub_versions_idem",
            "form_publication_versions",
            ["tenant_id", "form_id", "idempotency_key"],
            unique=True,
        )

    # Backfill current snapshot pointer into ledger (one row per form that already published).
    forms = sa.table(
        "tenant_lead_forms",
        sa.column("id", sa.String),
        sa.column("tenant_id", sa.String),
        sa.column("published_version", sa.Integer),
        sa.column("published_snapshot_v1", _JSON),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(
            forms.c.id,
            forms.c.tenant_id,
            forms.c.published_version,
            forms.c.published_snapshot_v1,
            forms.c.published_at,
            forms.c.created_at,
        ).where(forms.c.published_snapshot_v1.is_not(None))
    ).fetchall()
    import uuid
    from datetime import datetime, timezone

    versions = sa.table(
        "form_publication_versions",
        sa.column("id", sa.String),
        sa.column("tenant_id", sa.String),
        sa.column("form_id", sa.String),
        sa.column("version", sa.Integer),
        sa.column("snapshot", _JSON),
        sa.column("consent_pin", _JSON),
        sa.column("submission_pin_count", sa.Integer),
        sa.column("idempotency_key", sa.String),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        snap = row.published_snapshot_v1 or {}
        if not isinstance(snap, dict):
            snap = {}
        consent = snap.get("consent_pin") if isinstance(snap.get("consent_pin"), dict) else {}
        pub_at = row.published_at or row.created_at or now
        conn.execute(
            versions.insert().values(
                id=str(uuid.uuid4()),
                tenant_id=row.tenant_id,
                form_id=row.id,
                version=int(row.published_version or 1),
                snapshot=snap,
                consent_pin=consent,
                submission_pin_count=0,
                idempotency_key=None,
                published_at=pub_at,
                created_at=now,
            )
        )


def downgrade() -> None:
    op.drop_index("ix_form_pub_versions_idem", table_name="form_publication_versions")
    op.drop_index("ix_form_pub_versions_form_id", table_name="form_publication_versions")
    op.drop_index("ix_form_pub_versions_tenant_id", table_name="form_publication_versions")
    op.drop_index("ix_form_pub_versions_tenant_form", table_name="form_publication_versions")
    op.drop_table("form_publication_versions")
