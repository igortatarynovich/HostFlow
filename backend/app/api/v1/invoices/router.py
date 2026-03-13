"""API router for invoices."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.additional_service import ServiceOrder
from backend.app.models.company import Company
from backend.app.services.invoice_pdf import generate_invoice_pdf
from backend.app.services.notifications import send_webhook

from . import crud
from .schemas import (
    InvoiceCreate,
    InvoiceOut,
    InvoiceUpdate,
    PaymentCreate,
    PaymentOut,
    RefundCreate,
    RefundOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> InvoiceOut:
    """Create a new invoice."""
    db, tenant_id = db_tenant
    
    # Only managers and admins can create invoices
    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can create invoices",
        )
    
    try:
        invoice = await crud.create_invoice(
            db,
            str(tenant_id),
            payload.model_dump(),
            created_by=current_user.user_id,
        )
        await db.commit()
        await db.refresh(invoice)
        return InvoiceOut.model_validate(invoice)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("", response_model=List[InvoiceOut])
async def list_invoices(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    company_id: Optional[str] = Query(None),
    candidate_id: Optional[str] = Query(None),
    service_order_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[InvoiceOut]:
    """List invoices with optional filters."""
    db, tenant_id = db_tenant
    
    invoices = await crud.list_invoices(
        db,
        str(tenant_id),
        company_id=company_id,
        candidate_id=candidate_id,
        service_order_id=service_order_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    
    return [InvoiceOut.model_validate(inv) for inv in invoices]


@router.post("/from-service-order/{order_id}", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice_from_service_order(
    order_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> InvoiceOut:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can create invoices",
        )

    existing = await crud.get_invoice_by_service_order(db, tenant_id_str, order_id)
    if existing:
        return InvoiceOut.model_validate(existing)

    order_stmt = (
        select(ServiceOrder)
        .where(ServiceOrder.id == order_id, ServiceOrder.tenant_id == tenant_id_str)
        .limit(1)
    )
    order = (await db.execute(order_stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service order not found")
    if not order.company_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Service order must be linked to a company")
    await db.refresh(order, ["items"])
    if not order.items:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Service order has no billable items")

    company = await db.get(Company, order.company_id)
    company_extra = dict(getattr(company, "extra", {}) or {}) if company else {}
    billing = dict(company_extra.get("billing") or {}) if isinstance(company_extra.get("billing"), dict) else {}

    issue_date = datetime.now().date()
    due_date = issue_date + timedelta(days=int(billing.get("payment_terms_days") or 14))

    items_payload = []
    for idx, item in enumerate(order.items, start=1):
        service_name = getattr(getattr(item, "service", None), "name", None)
        service_code = getattr(getattr(item, "service", None), "code", None)
        items_payload.append(
            {
                "line_no": idx,
                "description": service_name or service_code or f"Service item {idx}",
                "qty": item.qty,
                "unit_price": item.unit_price,
                "vat_rate": item.vat_rate,
            }
        )

    billing_details = {
        "company_name": getattr(company, "legal_name", None) or getattr(company, "name", None),
        "email": billing.get("invoice_email") or getattr(company, "email", None),
        "tax_id": getattr(company, "tax_id", None),
        "address": billing.get("billing_address") or getattr(company, "address", None),
    }

    invoice = await crud.create_invoice(
        db,
        tenant_id_str,
        {
            "company_id": order.company_id,
            "service_order_id": order.id,
            "issue_date": issue_date,
            "due_date": due_date,
            "currency": getattr(order, "currency", None) or "PLN",
            "status": InvoiceStatus.draft.value,
            "items": items_payload,
            "billing_details": billing_details,
            "notes": getattr(order, "notes", None),
        },
        created_by=current_user.user_id,
    )
    await db.commit()
    await db.refresh(invoice)
    return InvoiceOut.model_validate(invoice)


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> InvoiceOut:
    """Get invoice by ID."""
    db, tenant_id = db_tenant
    
    invoice = await crud.get_invoice(db, str(tenant_id), invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    
    return InvoiceOut.model_validate(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> InvoiceOut:
    """Update invoice."""
    db, tenant_id = db_tenant
    
    # Only managers and admins can update invoices
    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can update invoices",
        )
    
    try:
        invoice = await crud.update_invoice(
            db,
            str(tenant_id),
            invoice_id,
            payload.model_dump(exclude_unset=True),
        )
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )
        await db.commit()
        await db.refresh(invoice)
        return InvoiceOut.model_validate(invoice)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/{invoice_id}/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def create_payment(
    invoice_id: str,
    payload: PaymentCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> PaymentOut:
    """Create a payment for an invoice."""
    db, tenant_id = db_tenant
    
    # Verify invoice exists
    invoice = await crud.get_invoice(db, str(tenant_id), invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    
    # Only managers and admins can create payments
    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can create payments",
        )
    
    try:
        payment = await crud.create_payment(
            db,
            str(tenant_id),
            invoice_id,
            payload.model_dump(),
        )
        await db.commit()
        await db.refresh(payment)
        return PaymentOut.model_validate(payment)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/payments/{payment_id}/refunds", response_model=RefundOut, status_code=status.HTTP_201_CREATED)
async def create_refund(
    payment_id: str,
    payload: RefundCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> RefundOut:
    """Create a refund for a payment."""
    db, tenant_id = db_tenant
    
    # Only managers and admins can create refunds
    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can create refunds",
        )
    
    try:
        refund = await crud.create_refund(
            db,
            str(tenant_id),
            payment_id,
            payload.model_dump(),
        )
        await db.commit()
        await db.refresh(refund)
        return RefundOut.model_validate(refund)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> Response:
    """Generate and download invoice PDF."""
    db, tenant_id = db_tenant
    
    invoice = await crud.get_invoice(db, str(tenant_id), invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    
    # Load items for PDF generation
    await db.refresh(invoice, ["items"])
    
    try:
        pdf_bytes = generate_invoice_pdf(invoice)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
            }
        )
    except Exception as e:
        logger.error(f"Failed to generate PDF for invoice {invoice_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF",
        ) from e


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
async def send_invoice(
    invoice_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> InvoiceOut:
    """Send invoice to client via email/webhook."""
    db, tenant_id = db_tenant
    
    # Only managers and admins can send invoices
    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can send invoices",
        )
    
    invoice = await crud.get_invoice(db, str(tenant_id), invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    
    # Only send issued or sent invoices
    if invoice.status not in (InvoiceStatus.issued.value, InvoiceStatus.sent.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send invoice with status {invoice.status}",
        )
    
    # Generate PDF
    await db.refresh(invoice, ["items"])
    try:
        pdf_bytes = generate_invoice_pdf(invoice)
        # In production, save PDF to storage and update pdf_file_id
        # For now, we'll just send via webhook
    except Exception as e:
        logger.error(f"Failed to generate PDF for invoice {invoice_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF for sending",
        ) from e
    
    # Send via webhook (email service will handle actual email sending)
    try:
        recipient_email = None
        if invoice.billing_details:
            recipient_email = invoice.billing_details.get("email")
        
        await send_webhook(
            "invoice.sent",
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "tenant_id": str(tenant_id),
                "recipient_email": recipient_email,
                "total_amount": str(invoice.total_amount),
                "currency": invoice.currency,
                "pdf_base64": None,  # In production, encode PDF as base64 or provide download URL
            }
        )
        
        # Update status to 'sent'
        invoice.status = InvoiceStatus.sent.value
        await db.commit()
        await db.refresh(invoice)
        
        return InvoiceOut.model_validate(invoice)
    except Exception as e:
        logger.error(f"Failed to send invoice {invoice_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invoice",
        ) from e


@router.post("/{invoice_id}/cancel", response_model=InvoiceOut)
async def cancel_invoice(
    invoice_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> InvoiceOut:
    """Cancel an invoice."""
    db, tenant_id = db_tenant
    
    # Only managers and admins can cancel invoices
    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can cancel invoices",
        )
    
    invoice = await crud.get_invoice(db, str(tenant_id), invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    
    # Cannot cancel paid invoices
    if invoice.status == InvoiceStatus.paid.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel paid invoice",
        )
    
    # Update status to cancelled
    invoice.status = InvoiceStatus.cancelled.value
    await db.commit()
    await db.refresh(invoice)
    
    return InvoiceOut.model_validate(invoice)
