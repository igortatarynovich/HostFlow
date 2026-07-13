"""Client preparation checklist — projection of existing workspace data."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import spa_client
from backend.app.models.company import Company
from backend.app.services.client_workspace import (
    billable_order_ids,
    billable_orders_missing_invoice,
    client_contract_marked,
    client_has_any_invoice,
    client_has_contact,
    client_requisites_ready,
    fetch_client_orders,
    filter_active_orders,
)


class ClientPreparationItemStatus(str, Enum):
    DONE = "done"
    MISSING = "missing"
    WARNING = "warning"


class ClientPreparationCheckItem(BaseModel):
    key: str
    status: ClientPreparationItemStatus
    soft: bool = Field(
        default=False,
        description="When true the item is advisory (contract) and does not block is_prepared.",
    )
    visible: bool = True
    title: str
    title_key: Optional[str] = None
    hint: Optional[str] = None
    hint_key: Optional[str] = None
    href: Optional[str] = None


class ClientPreparationChecklistDTO(BaseModel):
    entity_type: str = "client"
    entity_id: str
    is_prepared: bool = Field(
        description="Ready to work: order + requisites + contact (contract is soft).",
    )
    items: List[ClientPreparationCheckItem]


async def compute_client_preparation_checklist(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> ClientPreparationChecklistDTO:
    """Build the client preparation checklist from live company data."""
    tenant_id_str = str(tenant_id or "").strip()
    company_id_str = str(company_id or "").strip()
    href_detail = spa_client(company_id_str)
    href_orders = f"{href_detail}?ctab=orders"
    href_profile = f"{href_detail}?ctab=profile"
    href_invoices = f"{href_detail}?ctab=invoices"

    company = await db.get(Company, company_id_str) if company_id_str else None
    if company is None:
        return ClientPreparationChecklistDTO(
            entity_id=company_id_str,
            is_prepared=False,
            items=[],
        )

    owner_tid = str(getattr(company, "tenant_id", None) or "").strip() or tenant_id_str
    orders = await fetch_client_orders(db, tenant_id=owner_tid, company_id=company_id_str)
    active_orders = filter_active_orders(orders)
    has_order = bool(active_orders)
    has_requisites = client_requisites_ready(company)
    has_contact = client_has_contact(company)
    contract_ok = client_contract_marked(company)
    billable_ids = billable_order_ids(active_orders)
    has_invoice = await client_has_any_invoice(db, active_orders)
    needs_invoice = await billable_orders_missing_invoice(db, active_orders)

    items: list[ClientPreparationCheckItem] = [
        ClientPreparationCheckItem(
            key="services",
            status=ClientPreparationItemStatus.DONE if has_order else ClientPreparationItemStatus.MISSING,
            title="Services agreed / order created",
            title_key="app.client_preparation.services.title",
            hint="Create a service order so we know what the client buys.",
            hint_key="app.client_preparation.services.hint_missing",
            href=href_orders,
        ),
        ClientPreparationCheckItem(
            key="requisites",
            status=ClientPreparationItemStatus.DONE if has_requisites else ClientPreparationItemStatus.MISSING,
            title="Billing requisites on file",
            title_key="app.client_preparation.requisites.title",
            hint="Legal name, tax ID (NIP) and address are required to invoice.",
            hint_key="app.client_preparation.requisites.hint_missing",
            href=href_profile,
        ),
        ClientPreparationCheckItem(
            key="contact",
            status=ClientPreparationItemStatus.DONE if has_contact else ClientPreparationItemStatus.MISSING,
            title="Contact person added",
            title_key="app.client_preparation.contact.title",
            hint="Add someone to call or write to about the work.",
            hint_key="app.client_preparation.contact.hint_missing",
            href=href_profile,
        ),
        ClientPreparationCheckItem(
            key="contract",
            status=ClientPreparationItemStatus.DONE if contract_ok else ClientPreparationItemStatus.WARNING,
            soft=True,
            title="Contract signed" if contract_ok else "Contract not marked",
            title_key=(
                "app.client_preparation.contract.title_done"
                if contract_ok
                else "app.client_preparation.contract.title_warning"
            ),
            hint=(
                "Contract is on file — you can start work even before final signing if agreed."
                if contract_ok
                else "Mark the contract when signed — this does not block preparation."
            ),
            hint_key=(
                "app.client_preparation.contract.hint_done"
                if contract_ok
                else "app.client_preparation.contract.hint_warning"
            ),
            href=href_profile,
        ),
    ]

    if has_order:
        if has_invoice and not needs_invoice:
            invoice_status = ClientPreparationItemStatus.DONE
            invoice_title = "First invoice issued"
            invoice_title_key = "app.client_preparation.invoice.title_done"
            invoice_hint = "At least one invoice is linked to this client's orders."
            invoice_hint_key = "app.client_preparation.invoice.hint_done"
        elif needs_invoice:
            invoice_status = ClientPreparationItemStatus.MISSING
            invoice_title = "Issue the first invoice"
            invoice_title_key = "app.client_preparation.invoice.title_missing"
            invoice_hint = "A billable order exists with no invoice yet."
            invoice_hint_key = "app.client_preparation.invoice.hint_missing"
        else:
            invoice_status = ClientPreparationItemStatus.WARNING
            invoice_title = "Invoice after order confirmation"
            invoice_title_key = "app.client_preparation.invoice.title_pending"
            invoice_hint = "Confirm the order first — invoicing opens once the order is billable."
            invoice_hint_key = "app.client_preparation.invoice.hint_pending"

        items.append(
            ClientPreparationCheckItem(
                key="first_invoice",
                status=invoice_status,
                soft=invoice_status == ClientPreparationItemStatus.WARNING,
                title=invoice_title,
                title_key=invoice_title_key,
                hint=invoice_hint,
                hint_key=invoice_hint_key,
                href=href_invoices if invoice_status == ClientPreparationItemStatus.DONE else href_orders,
            )
        )

    is_prepared = has_order and has_requisites and has_contact
    return ClientPreparationChecklistDTO(
        entity_id=company_id_str,
        is_prepared=is_prepared,
        items=items,
    )


__all__ = [
    "ClientPreparationCheckItem",
    "ClientPreparationChecklistDTO",
    "ClientPreparationItemStatus",
    "compute_client_preparation_checklist",
]
