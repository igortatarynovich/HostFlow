"""API router for invoices."""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.invoice import InvoiceStatus

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
        status=status,
        limit=limit,
        offset=offset,
    )
    
    return [InvoiceOut.model_validate(inv) for inv in invoices]


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
    invoice = await crud.get_invoice(db, tenant_id, invoice_id)
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

