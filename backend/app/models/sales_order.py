"""Sales Service Order / Order Line / Billable Item (ADR-032)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

BILLING_TRIGGERS = (
    "candidate_hired",
    "candidate_started_work",
    "guarantee_period_passed",
    "milestone_accepted",
    "headcount_completed",
    "monthly_service_period_closed",
)


def now_utc() -> datetime:
    return datetime.utcnow()


class SalesOrder(Base):
    """Product: Service Order (Sales commercial deal snapshot)."""

    __tablename__ = "sales_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'cancelled')",
            name="ck_sales_orders_status",
        ),
        Index("ix_sales_orders_tenant_company", "tenant_id", "company_id"),
        Index("ix_sales_orders_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    own_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    client_account_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("client_accounts.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payer_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'open'"))
    currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    payment_term_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payment_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vat_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    guarantee_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    invoice_right_policy: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    billing_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    commercial_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"
    __table_args__ = (
        CheckConstraint("quantity_needed >= 1", name="ck_sales_order_lines_quantity"),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'cancelled')",
            name="ck_sales_order_lines_status",
        ),
        CheckConstraint(
            "billing_trigger IN ("
            "'candidate_hired', 'candidate_started_work', 'guarantee_period_passed', "
            "'milestone_accepted', 'headcount_completed', 'monthly_service_period_closed'"
            ")",
            name="ck_sales_order_lines_billing_trigger",
        ),
        Index("ix_sales_order_lines_order", "sales_order_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    sales_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    role_label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quantity_needed: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    charge_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    billing_trigger: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("'headcount_completed'")
    )
    guarantee_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'open'"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class SalesBillableItem(Base):
    __tablename__ = "sales_billable_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'invoiced', 'void')",
            name="ck_sales_billable_items_status",
        ),
        Index("ix_sales_billable_items_order", "sales_order_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    sales_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False
    )
    sales_order_line_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("sales_order_lines.id", ondelete="SET NULL"), nullable=True
    )
    trigger_code: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("1"))
    source_entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'pending'"))
    invoice_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
