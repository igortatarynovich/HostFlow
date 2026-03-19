"""
Invoice models for billing and invoicing module.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class InvoiceStatus(str, Enum):
    draft = "draft"
    issued = "issued"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class PaymentMethod(str, Enum):
    bank_transfer = "bank_transfer"
    card = "card"
    cash = "cash"
    online = "online"
    other = "other"


class PaymentStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"


class RefundStatus(str, Enum):
    initiated = "initiated"
    completed = "completed"
    cancelled = "cancelled"


class Invoice(Base):
    """Invoice model for billing."""

    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','issued','sent','paid','overdue','cancelled')",
            name="chk_invoice_status",
        ),
        CheckConstraint(
            "subtotal >= 0 AND vat_total >= 0 AND total_amount = subtotal + vat_total AND paid_amount >= 0",
            name="chk_invoice_amounts",
        ),
        Index("idx_invoices_tenant", "tenant_id"),
        Index("idx_invoices_company", "company_id"),
        Index("idx_invoices_candidate", "candidate_id"),
        Index("idx_invoices_status", "status"),
        Index("idx_invoices_due", "due_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("own_companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # References
    company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contract_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    order_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    service_order_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )

    # Invoice details
    invoice_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="PLN",
        server_default=text("'PLN'"),
    )

    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    vat_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )

    # Status and metadata
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=InvoiceStatus.draft.value,
        server_default=text("'draft'"),
    )
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pdf_file_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    billing_details: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql")),
        nullable=True,
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    items: Mapped[list["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InvoiceItem(Base):
    """Invoice line items."""

    __tablename__ = "invoice_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="chk_qty"),
        CheckConstraint("unit_price >= 0", name="chk_price"),
        Index("idx_invoice_items_invoice", "invoice_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    qty: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("1.00"),
        server_default=text("1"),
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("23.00"),
        server_default=text("23.00"),
    )

    # Computed fields (stored generated columns in PostgreSQL)
    net_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default=text("(qty * unit_price)"),
    )
    vat_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default=text("ROUND((qty * unit_price) * (vat_rate/100.0), 2)"),
    )
    gross_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default=text("ROUND((qty * unit_price) * (1 + vat_rate/100.0), 2)"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="items",
    )


class Payment(Base):
    """Payment records for invoices."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','failed')",
            name="chk_payment_status",
        ),
        CheckConstraint("amount > 0", name="chk_payment_amount"),
        Index("idx_payments_invoice", "invoice_id"),
        Index("idx_payments_tenant", "tenant_id"),
        Index("idx_payments_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="PLN",
        server_default=text("'PLN'"),
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
    )
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    provider_reference: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    reference_number: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PaymentStatus.confirmed.value,
        server_default=text("'confirmed'"),
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="payments",
    )
    refunds: Mapped[list["Refund"]] = relationship(
        "Refund",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Refund(Base):
    """Refund records for payments."""

    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint(
            "status IN ('initiated','completed','cancelled')",
            name="chk_refund_status",
        ),
        CheckConstraint("amount > 0", name="chk_refund_amount"),
        Index("idx_refunds_payment", "payment_id"),
        Index("idx_refunds_tenant", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refund_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=RefundStatus.initiated.value,
        server_default=text("'initiated'"),
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="refunds",
    )

