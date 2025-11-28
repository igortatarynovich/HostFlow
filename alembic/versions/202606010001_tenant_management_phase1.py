"""Tenant management foundation: add tenant metadata + licenses.

Revision ID: 202606010001_tenant_management_phase1
Revises: 202605200001_add_document_scan_sessions
Create Date: 2025-06-01 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


RevisionType = Union[str, Sequence[str], None]

revision: str = "202606010001_tenant_management_phase1"
down_revision: RevisionType = "202605200001"
branch_labels: RevisionType = None
depends_on: RevisionType = None


TENANT_TYPE_ENUM = sa.Enum("agency", "company", "platform", name="tenant_type_enum", native_enum=False)
TENANT_STATUS_ENUM = sa.Enum("active", "suspended", "trial", name="tenant_status_enum", native_enum=False)


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    return any(col["name"] == column for col in insp.get_columns(table))


def _has_index(conn, table: str, name: str) -> bool:
    insp = sa.inspect(conn)
    return any(idx["name"] == name for idx in insp.get_indexes(table))


def _create_usage_view() -> None:
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE VIEW tenant_usage AS
            SELECT
                t.id AS tenant_id,
                COALESCE(SUM(CASE WHEN lower(um.role) = 'recruiter' THEN 1 ELSE 0 END), 0) AS recruiter_count,
                COALESCE(SUM(CASE WHEN lower(um.role) = 'supervisor' THEN 1 ELSE 0 END), 0) AS supervisor_count,
                COALESCE(SUM(CASE WHEN lower(um.role) = 'client_manager' THEN 1 ELSE 0 END), 0) AS client_manager_count,
                COALESCE(SUM(CASE WHEN lower(um.role) = 'viewer' THEN 1 ELSE 0 END), 0) AS viewer_count,
                CAST(0 AS NUMERIC) AS storage_used_gb
            FROM tenants t
            LEFT JOIN user_memberships um ON um.tenant_id = t.id
            GROUP BY t.id
            """
        )
    )


def upgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "tenants"):
        if not _has_column(conn, "tenants", "type"):
            op.add_column(
                "tenants",
                sa.Column("type", TENANT_TYPE_ENUM, nullable=False, server_default="agency"),
            )
            conn.execute(sa.text("UPDATE tenants SET type = :value WHERE type IS NULL"), {"value": "agency"})

        if not _has_column(conn, "tenants", "parent_tenant_id"):
            op.add_column(
                "tenants",
                sa.Column("parent_tenant_id", sa.String(length=36), nullable=True),
            )
            op.create_foreign_key(
                "fk_tenants_parent",
                "tenants",
                "tenants",
                ["parent_tenant_id"],
                ["id"],
                ondelete="SET NULL",
            )

        if not _has_column(conn, "tenants", "status"):
            op.add_column(
                "tenants",
                sa.Column("status", TENANT_STATUS_ENUM, nullable=False, server_default="active"),
            )
            conn.execute(sa.text("UPDATE tenants SET status = :value WHERE status IS NULL"), {"value": "active"})

        if not _has_column(conn, "tenants", "client_portal_enabled"):
            op.add_column(
                "tenants",
                sa.Column("client_portal_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            )
            conn.execute(
                sa.text("UPDATE tenants SET client_portal_enabled = true WHERE client_portal_enabled IS NULL")
            )

        if not _has_column(conn, "tenants", "status_sharing_allowed"):
            op.add_column(
                "tenants",
                sa.Column("status_sharing_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
            conn.execute(
                sa.text("UPDATE tenants SET status_sharing_allowed = false WHERE status_sharing_allowed IS NULL")
            )

        if not _has_index(conn, "tenants", "ix_tenants_parent_tenant_id"):
            op.create_index(
                "ix_tenants_parent_tenant_id",
                "tenants",
                ["parent_tenant_id"],
                unique=False,
            )
        if not _has_index(conn, "tenants", "ix_tenants_status"):
            op.create_index(
                "ix_tenants_status",
                "tenants",
                ["status"],
                unique=False,
            )

    if not _has_table(conn, "tenant_licenses"):
        op.create_table(
            "tenant_licenses",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("plan", sa.String(length=64), nullable=False),
            sa.Column("max_recruiters", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_supervisors", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_client_managers", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_viewers", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_storage_gb", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_companies", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("expires_at", sa.Date(), nullable=True),
            sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notes", sa.Text(), nullable=True),
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
                name="fk_tenant_licenses_tenant",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_tenant_licenses_tenant_id",
            "tenant_licenses",
            ["tenant_id"],
            unique=True,
        )

    _create_usage_view()


def downgrade() -> None:
    op.execute(sa.text("DROP VIEW IF EXISTS tenant_usage"))
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("tenant_licenses"):
        op.drop_index("ix_tenant_licenses_tenant_id", table_name="tenant_licenses")
        op.drop_table("tenant_licenses")

    conn = op.get_bind()
    if _has_table(conn, "tenants"):
        if _has_column(conn, "tenants", "status_sharing_allowed"):
            op.drop_column("tenants", "status_sharing_allowed")
        if _has_column(conn, "tenants", "client_portal_enabled"):
            op.drop_column("tenants", "client_portal_enabled")
        if _has_column(conn, "tenants", "status"):
            if _has_index(conn, "tenants", "ix_tenants_status"):
                op.drop_index("ix_tenants_status", table_name="tenants")
            op.drop_column("tenants", "status")
        if _has_column(conn, "tenants", "parent_tenant_id"):
            if _has_index(conn, "tenants", "ix_tenants_parent_tenant_id"):
                op.drop_index("ix_tenants_parent_tenant_id", table_name="tenants")
            op.drop_constraint("fk_tenants_parent", "tenants", type_="foreignkey")
            op.drop_column("tenants", "parent_tenant_id")
        if _has_column(conn, "tenants", "type"):
            op.drop_column("tenants", "type")
