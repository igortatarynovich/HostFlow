"""Tenant Management Phase 3: seat requests

Revision ID: 202606150001_tenant_management_phase3
Revises: 202606010001_tenant_management_phase1
Create Date: 2025-06-15 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


RevisionType = Union[str, Sequence[str], None]

revision: str = "202606150001_tenant_management_phase3"
down_revision: RevisionType = "202606010001_tenant_management_phase1"
branch_labels: RevisionType = None
depends_on: RevisionType = None


REQUEST_STATUS_ENUM = sa.Enum(
    "pending",
    "approved",
    "rejected",
    name="tenant_seat_request_status_enum",
    native_enum=False,
)


def upgrade() -> None:
    REQUEST_STATUS_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tenant_seat_requests",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "status",
            REQUEST_STATUS_ENUM,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(length=36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_tenant_seat_requests_tenant",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_tenant_seat_requests_tenant_id",
        "tenant_seat_requests",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_seat_requests_status",
        "tenant_seat_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_seat_requests_status", table_name="tenant_seat_requests")
    op.drop_index("ix_tenant_seat_requests_tenant_id", table_name="tenant_seat_requests")
    op.drop_table("tenant_seat_requests")
    REQUEST_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
