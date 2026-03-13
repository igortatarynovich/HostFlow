"""Pydantic schemas for Invoicing API."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from backend.app.models.invoice import (
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
)


class InvoiceItemIn(BaseModel):
    """Input schema for invoice item."""

    line_no: int = Field(default=1, ge=1)
    description: str = Field(..., min_length=1)
    qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    vat_rate: Decimal = Field(default=Decimal("23.00"), ge=0, le=100)


class InvoiceItemOut(BaseModel):
    """Output schema for invoice item."""

    id: str
    invoice_id: str
    line_no: int
    description: str
    qty: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    net_total: Decimal
    vat_amount: Decimal
    gross_total: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    """Input schema for creating an invoice."""

    company_id: Optional[str] = None
    candidate_id: Optional[str] = None
    contract_id: Optional[str] = None
    order_id: Optional[str] = None
    service_order_id: Optional[str] = None
    invoice_number: Optional[str] = None  # Auto-generated if not provided
    issue_date: date
    due_date: date
    currency: str = Field(default="PLN", max_length=10)
    items: List[InvoiceItemIn] = Field(..., min_items=1)
    billing_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    status: str = Field(default=InvoiceStatus.draft.value)


class InvoiceUpdate(BaseModel):
    """Input schema for updating an invoice."""

    invoice_number: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    items: Optional[List[InvoiceItemIn]] = None
    billing_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class InvoiceOut(BaseModel):
    """Output schema for invoice."""

    id: str
    tenant_id: str
    company_id: Optional[str] = None
    candidate_id: Optional[str] = None
    contract_id: Optional[str] = None
    order_id: Optional[str] = None
    service_order_id: Optional[str] = None
    invoice_number: str
    issue_date: date
    due_date: date
    currency: str
    subtotal: Decimal
    vat_total: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    status: str
    payment_date: Optional[date] = None
    pdf_file_id: Optional[str] = None
    billing_details: Optional[Dict[str, Any]] = None
    latest_delivery_status: Optional[str] = None
    latest_delivery_reason: Optional[str] = None
    latest_delivery_at: Optional[datetime] = None
    latest_delivery_recipient: Optional[str] = None
    latest_delivery_subject: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItemOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InvoiceSendRequest(BaseModel):
    """Optional send composer payload for invoice delivery."""

    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class PaymentCreate(BaseModel):
    """Input schema for creating a payment."""

    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="PLN", max_length=10)
    payment_date: date
    method: str = Field(..., pattern="^(bank_transfer|card|cash|online|other)$")
    provider: Optional[str] = None
    provider_reference: Optional[str] = None
    reference_number: Optional[str] = None
    status: str = Field(default=PaymentStatus.confirmed.value)


class PaymentOut(BaseModel):
    """Output schema for payment."""

    id: str
    tenant_id: str
    invoice_id: str
    amount: Decimal
    currency: str
    payment_date: date
    method: str
    provider: Optional[str] = None
    provider_reference: Optional[str] = None
    reference_number: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RefundCreate(BaseModel):
    """Input schema for creating a refund."""

    amount: Decimal = Field(..., gt=0)
    reason: Optional[str] = None
    refund_date: Optional[date] = None
    status: str = Field(default=RefundStatus.initiated.value)


class RefundOut(BaseModel):
    """Output schema for refund."""

    id: str
    tenant_id: str
    payment_id: str
    amount: Decimal
    reason: Optional[str] = None
    refund_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceSummary(BaseModel):
    """Summary statistics for invoices."""

    total_count: int
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    overdue_count: int
    overdue_amount: Decimal


class InvoiceActivityOut(BaseModel):
    """Invoice activity timeline entry."""

    id: str
    tenant_id: str
    actor_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
