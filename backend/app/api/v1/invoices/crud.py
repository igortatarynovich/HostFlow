"""CRUD operations for invoices."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.company import Company
from backend.app.models.invoice import Invoice, InvoiceItem, Payment, Refund
from backend.app.models.invoice import InvoiceStatus


def _invoice_prefix(invoice_kind: str | None, tax_mode: str | None) -> str:
    kind = str(invoice_kind or "").strip().lower()
    if kind == "correction":
        return "KOR"
    if kind == "proforma":
        return "PRO"
    if kind == "invoice":
        return "INV"
    if kind == "vat" or str(tax_mode or "").strip().lower() == "standard_vat":
        return "FV"
    return "INV"


async def _generate_invoice_number(
    session: AsyncSession,
    *,
    tenant_id: str,
    issue_date: date,
    invoice_kind: str | None,
    tax_mode: str | None,
) -> str:
    """Generate tenant-local sequential invoice number with prefix."""
    prefix = _invoice_prefix(invoice_kind, tax_mode)
    year = issue_date.year
    month = issue_date.month
    like_pattern = f"{prefix}/{year}/{month:02d}/%"
    count_stmt = select(func.count()).select_from(Invoice).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_number.like(like_pattern),
    )
    count_result = await session.execute(count_stmt)
    seq = int(count_result.scalar_one() or 0) + 1
    return f"{prefix}/{year}/{month:02d}/{seq:04d}"


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _normalized_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _build_company_legal_address(company: Company | None) -> str | None:
    if not company:
        return None
    extra = _as_dict(getattr(company, "extra", {}) or {})
    billing = _as_dict(extra.get("billing"))
    billing_address = _as_dict(billing.get("billing_address"))
    parts = [
        _normalized_text(billing_address.get("country") or getattr(company, "country", None) or getattr(company, "country_code", None)),
        _normalized_text(billing_address.get("city") or getattr(company, "city", None)),
        _normalized_text(billing_address.get("street") or getattr(company, "address", None)),
        _normalized_text(billing_address.get("zip")),
    ]
    merged = ", ".join(part for part in parts if part)
    return merged or None


def _extract_primary_bank_account(company: Company | None) -> dict | None:
    if not company:
        return None
    extra = _as_dict(getattr(company, "extra", {}) or {})
    billing = _as_dict(extra.get("billing"))
    bank_accounts = billing.get("bank_accounts")
    if not isinstance(bank_accounts, list):
        return None
    normalized = [entry for entry in bank_accounts if isinstance(entry, dict)]
    if not normalized:
        return None
    return next((entry for entry in normalized if entry.get("is_primary")), normalized[0])


def _company_role(company: Company | None) -> str | None:
    if not company:
        return None
    extra = _as_dict(getattr(company, "extra", {}) or {})
    role = _normalized_text(extra.get("company_role"))
    return role.lower() if role else None


def _merge_issuer_defaults(
    *,
    billing_details: dict,
    issuer_company: Company | None,
) -> dict:
    merged = dict(billing_details or {})
    if not issuer_company:
        return merged
    merged["issuer_company_id"] = str(getattr(issuer_company, "id", "") or "") or merged.get("issuer_company_id")
    merged.setdefault("issuer_name", _normalized_text(getattr(issuer_company, "legal_name", None) or getattr(issuer_company, "name", None)))
    merged.setdefault("issuer_tax_id", _normalized_text(getattr(issuer_company, "tax_id", None)))
    merged.setdefault("issuer_address", _build_company_legal_address(issuer_company))
    issuer_bank = _extract_primary_bank_account(issuer_company)
    if issuer_bank:
        merged.setdefault(
            "issuer_bank_account",
            {
                "bank_name": _normalized_text(issuer_bank.get("bank_name")),
                "iban": _normalized_text(issuer_bank.get("iban")),
                "swift_bic": _normalized_text(issuer_bank.get("swift_bic") or issuer_bank.get("swift")),
                "country": _normalized_text(issuer_bank.get("country")),
                "label": _normalized_text(issuer_bank.get("label")),
            },
        )
    return merged


async def _resolve_issuer_company_for_actor(
    session: AsyncSession,
    *,
    tenant_id: str,
    issuer_company_id: str | None,
    actor_id: str | None,
) -> Company | None:
    issuer_id = _normalized_text(issuer_company_id)
    if not issuer_id:
        return None
    issuer_company = await session.get(Company, issuer_id)
    if not issuer_company or str(getattr(issuer_company, "tenant_id", "")) != str(tenant_id):
        raise ValueError("Issuer company not found")
    if _company_role(issuer_company) != "operating":
        raise ValueError("Issuer company must be an operating company")
    actor = _normalized_text(actor_id)
    if actor and actor not in {
        _normalized_text(getattr(issuer_company, "owner_user_id", None)),
        _normalized_text(getattr(issuer_company, "manager_user_id", None)),
    }:
        raise ValueError("Issuer company must be one of your managed companies")
    return issuer_company


def _merge_billing_defaults(
    *,
    billing_details: dict | None,
    client_company: Company | None,
) -> dict:
    merged = dict(billing_details or {})
    if client_company:
        merged.setdefault("company_name", _normalized_text(getattr(client_company, "legal_name", None) or getattr(client_company, "name", None)))
        merged.setdefault("tax_id", _normalized_text(getattr(client_company, "tax_id", None)))
        merged.setdefault("address", _build_company_legal_address(client_company))
    return merged


def _validate_invoice_billing_details(billing_details: dict | None) -> dict:
    details = dict(billing_details or {})
    issuer_bank = _as_dict(details.get("issuer_bank_account"))
    invoice_kind = _normalized_text(details.get("invoice_kind")) or "invoice"
    required_checks = [
        ("company_name", "Client legal name is required for invoices"),
        ("tax_id", "Client tax ID/NIP is required for invoices"),
        ("address", "Client legal address is required for invoices"),
        ("issuer_name", "Issuer legal name is required for invoices"),
        ("issuer_tax_id", "Issuer tax ID/NIP is required for invoices"),
        ("issuer_address", "Issuer legal address is required for invoices"),
    ]
    for key, message in required_checks:
        if not _normalized_text(details.get(key)):
            raise ValueError(message)
    if not _normalized_text(issuer_bank.get("iban")):
        raise ValueError("Issuer bank account is required for invoices")
    if invoice_kind == "correction":
        if not _normalized_text(details.get("correction_of_invoice_id")):
            raise ValueError("Correction invoice must reference the original invoice")
        if not _normalized_text(details.get("correction_of_invoice_number")):
            raise ValueError("Correction invoice must include the original invoice number")
        if not _normalized_text(details.get("correction_reason")):
            raise ValueError("Correction invoice reason is required")
    return details


async def create_invoice(
    session: AsyncSession,
    tenant_id: str,
    payload: dict,
    created_by: Optional[str] = None,
) -> Invoice:
    """Create a new invoice with items."""
    now = datetime.now(timezone.utc)
    issue_date = payload.get("issue_date")
    if isinstance(issue_date, str):
        issue_date = date.fromisoformat(issue_date)
    
    tenant_id_str = str(tenant_id)
    client_company: Company | None = None
    if payload.get("company_id"):
        client_company = await session.get(Company, payload.get("company_id"))
        if client_company and str(getattr(client_company, "tenant_id", "")) != tenant_id_str:
            client_company = None
    payload_billing = _as_dict(payload.get("billing_details"))
    issuer_company = await _resolve_issuer_company_for_actor(
        session,
        tenant_id=tenant_id_str,
        issuer_company_id=_normalized_text(payload_billing.get("issuer_company_id")),
        actor_id=created_by,
    )
    billing_details = _validate_invoice_billing_details(
        _merge_issuer_defaults(
            billing_details=_merge_billing_defaults(
                billing_details=payload_billing,
                client_company=client_company,
            ),
            issuer_company=issuer_company,
        )
    )
    
    # Generate invoice number if not provided
    invoice_number = _normalized_text(payload.get("invoice_number"))
    if not invoice_number:
        invoice_number = await _generate_invoice_number(
            session,
            tenant_id=tenant_id_str,
            issue_date=issue_date or now.date(),
            invoice_kind=_normalized_text(billing_details.get("invoice_kind")),
            tax_mode=_normalized_text(billing_details.get("tax_mode")),
        )
    
    # Create invoice
    invoice = Invoice(
        id=str(uuid4()),
        tenant_id=tenant_id_str,
        company_id=payload.get("company_id"),
        candidate_id=payload.get("candidate_id"),
        contract_id=payload.get("contract_id"),
        order_id=payload.get("order_id"),
        service_order_id=payload.get("service_order_id"),
        invoice_number=invoice_number,
        issue_date=issue_date or now.date(),
        due_date=date.fromisoformat(payload["due_date"]) if isinstance(payload.get("due_date"), str) else payload.get("due_date"),
        currency=payload.get("currency", "PLN"),
        status=payload.get("status", InvoiceStatus.draft.value),
        billing_details=billing_details,
        notes=payload.get("notes"),
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    
    session.add(invoice)
    await session.flush()
    
    # Create invoice items
    items_data = payload.get("items", [])
    for idx, item_data in enumerate(items_data, start=1):
        item = InvoiceItem(
            id=str(uuid4()),
            invoice_id=invoice.id,
            line_no=item_data.get("line_no", idx),
            description=item_data["description"],
            qty=Decimal(str(item_data["qty"])),
            unit_price=Decimal(str(item_data["unit_price"])),
            vat_rate=Decimal(str(item_data.get("vat_rate", "23.00"))),
            created_at=now,
        )
        session.add(item)
    
    await session.flush()
    
    # Recalculate totals (PostgreSQL triggers will do this, but we can also do it manually)
    await _recalculate_invoice_totals(session, invoice.id)
    
    await session.refresh(invoice)
    return invoice


async def _recalculate_invoice_totals(session: AsyncSession, invoice_id: str) -> None:
    """Recalculate invoice totals from items."""
    # In PostgreSQL, this is done by triggers, but we can also do it manually
    result = await session.execute(
        select(
            func.sum(InvoiceItem.net_total).label("subtotal"),
            func.sum(InvoiceItem.vat_amount).label("vat_total"),
            func.sum(InvoiceItem.gross_total).label("total"),
        ).where(InvoiceItem.invoice_id == invoice_id)
    )
    row = result.first()
    if row:
        await session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(
                subtotal=row.subtotal or Decimal("0"),
                vat_total=row.vat_total or Decimal("0"),
                total_amount=row.total or Decimal("0"),
                updated_at=datetime.now(timezone.utc),
            )
        )


async def get_invoice(
    session: AsyncSession,
    tenant_id: str,
    invoice_id: str,
) -> Optional[Invoice]:
    """Get invoice by ID."""
    tenant_id_str = str(tenant_id)
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id_str)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_invoices(
    session: AsyncSession,
    tenant_id: str,
    *,
    company_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    service_order_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Invoice]:
    """List invoices with filters."""
    # tenant_id is stored as VARCHAR, convert UUID to string for comparison
    tenant_id_str = str(tenant_id)
    stmt = select(Invoice).where(Invoice.tenant_id == tenant_id_str)
    
    if company_id:
        stmt = stmt.where(Invoice.company_id == company_id)
    if candidate_id:
        stmt = stmt.where(Invoice.candidate_id == candidate_id)
    if service_order_id:
        stmt = stmt.where(Invoice.service_order_id == service_order_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    
    stmt = stmt.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_invoice_by_service_order(
    session: AsyncSession,
    tenant_id: str,
    service_order_id: str,
) -> Optional[Invoice]:
    tenant_id_str = str(tenant_id)
    stmt = (
        select(Invoice)
        .where(
            Invoice.tenant_id == tenant_id_str,
            Invoice.service_order_id == service_order_id,
        )
        .order_by(Invoice.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_invoice(
    session: AsyncSession,
    tenant_id: str,
    invoice_id: str,
    payload: dict,
    actor_id: Optional[str] = None,
) -> Optional[Invoice]:
    """Update invoice."""
    tenant_id_str = str(tenant_id)
    invoice = await get_invoice(session, tenant_id_str, invoice_id)
    if not invoice:
        return None
    
    if invoice.status != InvoiceStatus.draft.value:
        raise ValueError("Only draft invoices can be edited. Create a correction invoice instead.")
    
    # Update fields
    next_billing_details = _as_dict(invoice.billing_details)
    if "issue_date" in payload:
        invoice.issue_date = date.fromisoformat(payload["issue_date"]) if isinstance(payload["issue_date"], str) else payload["issue_date"]
    if "invoice_number" in payload:
        invoice.invoice_number = _normalized_text(payload["invoice_number"]) or invoice.invoice_number
    if "due_date" in payload:
        invoice.due_date = date.fromisoformat(payload["due_date"]) if isinstance(payload["due_date"], str) else payload["due_date"]
    if "currency" in payload:
        invoice.currency = payload["currency"]
    if "billing_details" in payload:
        next_billing_details = _as_dict(payload["billing_details"])
    if "notes" in payload:
        invoice.notes = payload["notes"]
    if "status" in payload:
        invoice.status = payload["status"]

    client_company: Company | None = None
    if invoice.company_id:
        client_company = await session.get(Company, invoice.company_id)
        if client_company and str(getattr(client_company, "tenant_id", "")) != tenant_id_str:
            client_company = None
    issuer_company = await _resolve_issuer_company_for_actor(
        session,
        tenant_id=tenant_id_str,
        issuer_company_id=_normalized_text(next_billing_details.get("issuer_company_id")),
        actor_id=actor_id,
    )
    invoice.billing_details = _validate_invoice_billing_details(
        _merge_issuer_defaults(
            billing_details=_merge_billing_defaults(
                billing_details=next_billing_details,
                client_company=client_company,
            ),
            issuer_company=issuer_company,
        )
    )
    
    # Update items if provided
    if "items" in payload:
        # Delete existing items
        await session.execute(
            delete(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
        )
        # Create new items
        for idx, item_data in enumerate(payload["items"], start=1):
            item = InvoiceItem(
                id=str(uuid4()),
                invoice_id=invoice.id,
                line_no=item_data.get("line_no", idx),
                description=item_data["description"],
                qty=Decimal(str(item_data["qty"])),
                unit_price=Decimal(str(item_data["unit_price"])),
                vat_rate=Decimal(str(item_data.get("vat_rate", "23.00"))),
                created_at=datetime.now(timezone.utc),
            )
            session.add(item)
        
        await _recalculate_invoice_totals(session, invoice.id)
    
    invoice.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(invoice)
    return invoice


async def create_payment(
    session: AsyncSession,
    tenant_id: str,
    invoice_id: str,
    payload: dict,
) -> Payment:
    """Create a payment for an invoice."""
    tenant_id_str = str(tenant_id)
    payment = Payment(
        id=str(uuid4()),
        tenant_id=tenant_id_str,
        invoice_id=invoice_id,
        amount=Decimal(str(payload["amount"])),
        currency=payload.get("currency", "PLN"),
        payment_date=date.fromisoformat(payload["payment_date"]) if isinstance(payload.get("payment_date"), str) else payload.get("payment_date"),
        method=payload["method"],
        provider=payload.get("provider"),
        provider_reference=payload.get("provider_reference"),
        reference_number=payload.get("reference_number"),
        status=payload.get("status", PaymentStatus.confirmed.value),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    session.add(payment)
    await session.flush()
    
    # Recalculate paid amount (PostgreSQL triggers will do this)
    await _recalculate_paid_amount(session, invoice_id)
    
    await session.refresh(payment)
    return payment


async def _recalculate_paid_amount(session: AsyncSession, invoice_id: str) -> None:
    """Recalculate paid amount from payments and refunds."""
    # In PostgreSQL, this is done by triggers
    result = await session.execute(
        select(
            func.sum(Payment.amount).label("paid"),
        ).where(
            Payment.invoice_id == invoice_id,
            Payment.status == PaymentStatus.confirmed.value,
        )
    )
    row = result.first()
    paid = row.paid or Decimal("0")
    
    # Subtract refunds
    refund_result = await session.execute(
        select(
            func.sum(Refund.amount).label("refunded"),
        ).join(Payment).where(
            Payment.invoice_id == invoice_id,
            Refund.status == RefundStatus.completed.value,
        )
    )
    refund_row = refund_result.first()
    if refund_row and refund_row.refunded:
        paid -= refund_row.refunded
    
    await session.execute(
        update(Invoice)
        .where(Invoice.id == invoice_id)
        .values(
            paid_amount=max(Decimal("0"), paid),
            updated_at=datetime.now(timezone.utc),
        )
    )
    
    # Update status if fully paid
    invoice = await session.get(Invoice, invoice_id)
    if invoice and invoice.paid_amount >= invoice.total_amount and invoice.total_amount > 0:
        await session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(
                status=InvoiceStatus.paid.value,
                payment_date=date.today(),
            )
        )


async def create_refund(
    session: AsyncSession,
    tenant_id: str,
    payment_id: str,
    payload: dict,
) -> Refund:
    """Create a refund for a payment."""
    tenant_id_str = str(tenant_id)
    refund = Refund(
        id=str(uuid4()),
        tenant_id=tenant_id_str,
        payment_id=payment_id,
        amount=Decimal(str(payload["amount"])),
        reason=payload.get("reason"),
        refund_date=payload.get("refund_date") or date.today(),
        status=payload.get("status", RefundStatus.initiated.value),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    session.add(refund)
    await session.flush()
    
    # Get payment to find invoice_id
    payment = await session.get(Payment, payment_id)
    if payment:
        await _recalculate_paid_amount(session, payment.invoice_id)
    
    await session.refresh(refund)
    return refund
