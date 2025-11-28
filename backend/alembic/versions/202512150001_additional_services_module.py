"""Additional services module core tables."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202512150001_additional_services_module"
down_revision: Union[str, Sequence[str], None] = "202512120001_company_profile_expansion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SERVICE_UNIT_ENUM = (
    "piece",
    "person",
    "hour",
    "package",
)

SERVICE_ORDER_STATUS_ENUM = (
    "draft",
    "quoted",
    "approved",
    "scheduled",
    "in_progress",
    "delivered",
    "cancelled",
    "refunded",
)

SERVICE_ITEM_STATUS_ENUM = (
    "pending",
    "scheduled",
    "in_progress",
    "delivered",
    "cancelled",
)

SERVICE_SCHEDULE_STATUS_ENUM = (
    "reserved",
    "confirmed",
    "completed",
    "no_show",
    "cancelled",
)


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column(
            "unit",
            sa.Enum(*SERVICE_UNIT_ENUM, name="service_unit_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PLN"),
        sa.Column("vat_rate", sa.Numeric(4, 2), nullable=False, server_default="23"),
        sa.Column("requires_schedule", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_candidate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result_document_type", sa.String(length=100), nullable=True),
        sa.Column("requires_documents", sa.JSON(), nullable=True),
        sa.Column("sla_hours", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "code", name="uq_services_tenant_code"),
    )
    op.create_index("ix_services_tenant", "services", ["tenant_id"])
    op.create_index("ix_services_tenant_active", "services", ["tenant_id", "is_active"])

    op.create_table(
        "service_orders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=True),
        sa.Column("vacancy_id", sa.String(length=36), nullable=True),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*SERVICE_ORDER_STATUS_ENUM, name="service_order_status_enum", native_enum=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PLN"),
        sa.Column("vat_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column("assigned_to", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("audit", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "((CASE WHEN candidate_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN vacancy_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN company_id IS NOT NULL THEN 1 ELSE 0 END)) = 1",
            name="ck_service_orders_owner",
        ),
    )
    op.create_index("ix_service_orders_tenant", "service_orders", ["tenant_id"])
    op.create_index("ix_service_orders_tenant_status", "service_orders", ["tenant_id", "status"])
    op.create_index("ix_service_orders_candidate", "service_orders", ["tenant_id", "candidate_id"])
    op.create_index("ix_service_orders_vacancy", "service_orders", ["tenant_id", "vacancy_id"])
    op.create_index("ix_service_orders_company", "service_orders", ["tenant_id", "company_id"])

    op.create_table(
        "service_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=False),
        sa.Column("qty", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("vat_rate", sa.Numeric(4, 2), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(*SERVICE_ITEM_STATUS_ENUM, name="service_item_status_enum", native_enum=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("required_documents", sa.JSON(), nullable=True),
        sa.Column("result_document_type", sa.String(length=100), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["service_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_service_items_tenant", "service_items", ["tenant_id"])
    op.create_index("ix_service_items_tenant_status", "service_items", ["tenant_id", "status"])
    op.create_index("ix_service_items_order", "service_items", ["tenant_id", "order_id"])
    op.create_index("ix_service_items_service", "service_items", ["tenant_id", "service_id"])

    op.create_table(
        "service_schedule",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=True),
        sa.Column("slot_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slot_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*SERVICE_SCHEDULE_STATUS_ENUM, name="service_schedule_status_enum", native_enum=False),
            nullable=False,
            server_default="reserved",
        ),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["service_items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_service_schedule_tenant", "service_schedule", ["tenant_id"])
    op.create_index("ix_service_schedule_tenant_status", "service_schedule", ["tenant_id", "status"])
    op.create_index("ix_service_schedule_item", "service_schedule", ["tenant_id", "item_id"])

    op.create_table(
        "service_attachments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["service_items.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_index("ix_service_attachments_item", table_name="service_attachments")
    op.drop_index("ix_service_attachments_tenant", table_name="service_attachments")
    op.drop_table("service_attachments")

    op.drop_index("ix_service_schedule_item", table_name="service_schedule")
    op.drop_index("ix_service_schedule_tenant_status", table_name="service_schedule")
    op.drop_index("ix_service_schedule_tenant", table_name="service_schedule")
    op.drop_table("service_schedule")

    op.drop_index("ix_service_items_service", table_name="service_items")
    op.drop_index("ix_service_items_order", table_name="service_items")
    op.drop_index("ix_service_items_tenant_status", table_name="service_items")
    op.drop_index("ix_service_items_tenant", table_name="service_items")
    op.drop_table("service_items")

    op.drop_index("ix_service_orders_company", table_name="service_orders")
    op.drop_index("ix_service_orders_vacancy", table_name="service_orders")
    op.drop_index("ix_service_orders_candidate", table_name="service_orders")
    op.drop_index("ix_service_orders_tenant_status", table_name="service_orders")
    op.drop_index("ix_service_orders_tenant", table_name="service_orders")
    op.drop_table("service_orders")

    op.drop_index("ix_services_tenant_active", table_name="services")
    op.drop_index("ix_services_tenant", table_name="services")
    op.drop_table("services")

    for enum_name in (
        "service_schedule_status_enum",
        "service_item_status_enum",
        "service_order_status_enum",
        "service_unit_enum",
    ):
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
    op.create_index("ix_service_attachments_tenant", "service_attachments", ["tenant_id"])
    op.create_index("ix_service_attachments_item", "service_attachments", ["tenant_id", "item_id"])
