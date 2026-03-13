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
from backend.app.models.audit import ActivityLog
from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.additional_service import ServiceOrder
from backend.app.models.company import Company
from backend.app.services.audit import log_activity
from backend.app.services.invoice_pdf import generate_invoice_pdf
from backend.app.services.notifications import send_webhook

from . import crud
from .schemas import (
    InvoiceActivityOut,
    InvoiceCreate,
    InvoiceOut,
    InvoiceSendRequest,
    InvoiceUpdate,
    PaymentCreate,
    PaymentOut,
    RefundCreate,
    RefundOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invoices", tags=["invoices"])


async def _log_invoice_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    invoice: Invoice,
    action: str,
    actor_id: str | None,
    payload: dict | None = None,
) -> None:
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        target_type="invoice",
        target_id=invoice.id,
        payload={
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "company_id": invoice.company_id,
            "service_order_id": invoice.service_order_id,
            **(payload or {}),
        },
    )


async def _build_delivery_lookup(
    db: AsyncSession,
    *,
    tenant_id: str,
    invoice_ids: List[str],
) -> dict[str, dict]:
    if not invoice_ids:
        return {}
    stmt = (
        select(ActivityLog)
        .where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_type == "invoice",
            ActivityLog.target_id.in_(invoice_ids),
            ActivityLog.action.in_(["invoice.sent", "invoice.send_failed"]),
        )
        .order_by(ActivityLog.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    lookup: dict[str, dict] = {}
    for row in rows:
        target_id = str(row.target_id or "").strip()
        if not target_id or target_id in lookup:
            continue
        payload = dict(row.payload or {})
        lookup[target_id] = {
            "latest_delivery_status": payload.get("delivery_status") or ("failed" if row.action == "invoice.send_failed" else "sent"),
            "latest_delivery_reason": payload.get("reason"),
            "latest_delivery_at": row.created_at,
            "latest_delivery_recipient": payload.get("recipient_email"),
            "latest_delivery_subject": payload.get("subject"),
        }
    return lookup


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
            created_by=current_user.sub,
        )
        await _log_invoice_activity(
            db,
            tenant_id=str(tenant_id),
            invoice=invoice,
            action="invoice.created",
            actor_id=current_user.sub,
            payload={"source": "manual"},
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
    delivery_lookup = await _build_delivery_lookup(
        db,
        tenant_id=str(tenant_id),
        invoice_ids=[str(inv.id) for inv in invoices],
    )

    return [
        InvoiceOut.model_validate(
            {
                **InvoiceOut.model_validate(inv).model_dump(),
                **delivery_lookup.get(str(inv.id), {}),
            }
        )
        for inv in invoices
    ]


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
        created_by=current_user.sub,
    )
    await _log_invoice_activity(
        db,
        tenant_id=tenant_id_str,
        invoice=invoice,
        action="invoice.created",
        actor_id=current_user.sub,
        payload={"source": "service_order", "service_order_id": order.id},
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


@router.get("/{invoice_id}/activity", response_model=List[InvoiceActivityOut])
async def get_invoice_activity(
    invoice_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
) -> List[InvoiceActivityOut]:
    """Get invoice activity timeline entries."""
    db, tenant_id = db_tenant

    invoice = await crud.get_invoice(db, str(tenant_id), invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    stmt = (
        select(ActivityLog)
        .where(
            ActivityLog.tenant_id == str(tenant_id),
            ActivityLog.target_type == "invoice",
            ActivityLog.target_id == invoice_id,
        )
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        InvoiceActivityOut(
            id=row.id,
            tenant_id=row.tenant_id,
            actor_id=row.actor_id,
            action=row.action,
            target_type=row.target_type,
            target_id=row.target_id,
            payload=dict(row.payload or {}),
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.patch("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> InvoiceOut:
    """Update invoice."""
    db, tenant_id = db_tenant
    existing_invoice = await crud.get_invoice(db, str(tenant_id), invoice_id)
    previous_status = existing_invoice.status if existing_invoice else None
    
    # Only managers and admins can update invoices
    if current_user.role not in (Role.manager, Role.admin, Role.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can update invoices",
        )
    if not existing_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    
    try:
        invoice = await crud.update_invoice(
            db,
            str(tenant_id),
            invoice_id,
            payload.model_dump(exclude_unset=True),
            actor_id=current_user.sub,
        )
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )
        action = "invoice.updated"
        activity_payload: dict = {}
        next_status = payload.status
        if next_status and next_status != previous_status:
            action = "invoice.status_changed"
            activity_payload = {
                "previous_status": previous_status,
                "next_status": next_status,
            }
            if next_status == InvoiceStatus.issued.value:
                action = "invoice.issued"
            elif next_status == InvoiceStatus.cancelled.value:
                action = "invoice.cancelled"
        await _log_invoice_activity(
            db,
            tenant_id=str(tenant_id),
            invoice=invoice,
            action=action,
            actor_id=current_user.sub,
            payload=activity_payload,
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
        await db.refresh(invoice)
        await _log_invoice_activity(
            db,
            tenant_id=str(tenant_id),
            invoice=invoice,
            action="invoice.payment_recorded",
            actor_id=current_user.sub,
            payload={
                "payment_id": payment.id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "method": payment.method,
                "paid_amount": str(invoice.paid_amount),
            },
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
    payload: InvoiceSendRequest | None = None,
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
        send_payload = payload.model_dump(exclude_none=True) if payload else {}
        recipient_email = send_payload.get("recipient_email")
        if invoice.billing_details:
            recipient_email = recipient_email or invoice.billing_details.get("email")
        if not recipient_email:
            await _log_invoice_activity(
                db,
                tenant_id=str(tenant_id),
                invoice=invoice,
                action="invoice.send_failed",
                actor_id=current_user.sub,
                payload={"delivery_status": "failed", "reason": "missing_recipient_email"},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invoice recipient email is required",
            )

        if invoice.billing_details is None:
            invoice.billing_details = {}
        invoice.billing_details["email"] = recipient_email

        subject = str(send_payload.get("subject") or f"Invoice {invoice.invoice_number} from HostFlow").strip()
        body = str(
            send_payload.get("body")
            or (
                f"Please find invoice {invoice.invoice_number} attached.\n"
                f"Total: {invoice.total_amount} {invoice.currency}\n"
                f"Due date: {invoice.due_date}"
            )
        ).strip()

        delivery = await send_webhook(
            "invoice.sent",
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "tenant_id": str(tenant_id),
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "total_amount": str(invoice.total_amount),
                "currency": invoice.currency,
                "pdf_base64": None,  # In production, encode PDF as base64 or provide download URL
            }
        )
        delivery_status = str(delivery.get("delivery_status") or "failed")
        delivery_reason = delivery.get("reason")
        http_status = delivery.get("http_status")
        if delivery_status == "failed":
            await _log_invoice_activity(
                db,
                tenant_id=str(tenant_id),
                invoice=invoice,
                action="invoice.send_failed",
                actor_id=current_user.sub,
                payload={
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "body": body,
                    "delivery_status": delivery_status,
                    "reason": delivery_reason,
                    "http_status": http_status,
                },
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to deliver invoice",
            )
        
        # Update status to 'sent'
        invoice.status = InvoiceStatus.sent.value
        await _log_invoice_activity(
            db,
            tenant_id=str(tenant_id),
            invoice=invoice,
            action="invoice.sent",
            actor_id=current_user.sub,
            payload={
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "delivery_status": delivery_status,
                "reason": delivery_reason,
                "http_status": http_status,
            },
        )
        await db.commit()
        await db.refresh(invoice)
        
        return InvoiceOut.model_validate(invoice)
    except HTTPException:
        raise
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
    await _log_invoice_activity(
        db,
        tenant_id=str(tenant_id),
        invoice=invoice,
        action="invoice.cancelled",
        actor_id=current_user.sub,
        payload={},
    )
    await db.commit()
    await db.refresh(invoice)
    
    return InvoiceOut.model_validate(invoice)
