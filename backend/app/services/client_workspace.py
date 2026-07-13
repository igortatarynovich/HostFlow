"""Shared client workspace signals used by next-action and preparation checklist.

Not a new entity — projections over company, service_orders, contacts, invoices,
and contract markers already on the company row / extra JSON.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.additional_service import ServiceOrder, ServiceOrderStatus
from backend.app.models.company import Company
from backend.app.models.invoice import Invoice

CLIENT_ACTIVE_ORDER_EXCLUDED_STATUSES: frozenset[str] = frozenset(
    {ServiceOrderStatus.cancelled.value}
)
# An order the manager can still append a new service line to: not yet in
# execution, not completed/cancelled, and (checked separately) not invoiced.
CLIENT_EDITABLE_ORDER_STATUSES: frozenset[str] = frozenset(
    {ServiceOrderStatus.draft.value, ServiceOrderStatus.confirmed.value}
)
CLIENT_BILLABLE_ORDER_STATUSES: frozenset[str] = frozenset(
    {
        ServiceOrderStatus.confirmed.value,
        ServiceOrderStatus.in_progress.value,
        ServiceOrderStatus.completed.value,
    }
)
CLIENT_INVOICE_VOID_STATUSES: frozenset[str] = frozenset({"cancelled", "void", "voided"})

_CONTRACT_SIGNED_STAGE_CODES: frozenset[str] = frozenset({"contract_signed", "active"})
_CONTRACT_SIGNED_STATUSES: frozenset[str] = frozenset(
    {"signed", "active", "completed", "in_force", "executed", "valid"}
)


def client_has_contact(company: Company) -> bool:
    """A contact person to reach out to (contacts map, or phone/email on file)."""
    try:
        from backend.app.modules.companies.crud import _normalize_contacts_map

        contacts_map = _normalize_contacts_map(getattr(company, "contacts", {}), strict=False)
        if contacts_map:
            return True
    except Exception:  # pragma: no cover - defensive
        contacts = getattr(company, "contacts", None)
        if isinstance(contacts, dict) and contacts:
            return True
    return bool(
        str(getattr(company, "email", "") or "").strip()
        or str(getattr(company, "phone", "") or "").strip()
    )


def client_requisites_ready(company: Company) -> bool:
    """Invoice-blocking fields: tax_id (NIP) + legal address."""
    tax_ok = bool(str(getattr(company, "tax_id", "") or "").strip())
    address = str(getattr(company, "address", "") or "").strip()
    if not address:
        extra = getattr(company, "extra", None)
        if isinstance(extra, dict):
            billing = extra.get("billing")
            if isinstance(billing, dict):
                address = str(billing.get("billing_address") or "").strip()
    return tax_ok and bool(address)


def client_contract_marked(company: Company) -> bool:
    """Soft prep signal: pipeline stage, explicit flag, or a signed contract row."""
    stage = str(getattr(company, "client_stage", "") or "").strip().lower()
    if stage in _CONTRACT_SIGNED_STAGE_CODES:
        return True
    extra = getattr(company, "extra", None)
    if not isinstance(extra, dict):
        return False
    if extra.get("contract_signed") is True:
        return True
    for key in ("contracts", "contracts_history", "contract_history"):
        block = extra.get(key)
        if not isinstance(block, list):
            continue
        for entry in block:
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status") or "").strip().lower()
            if status in _CONTRACT_SIGNED_STATUSES:
                return True
    return False


async def fetch_client_orders(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> list[ServiceOrder]:
    owner_tid = str(tenant_id or "").strip()
    company_id_str = str(company_id or "").strip()
    if not owner_tid or not company_id_str:
        return []
    return list(
        (
            await db.execute(
                select(ServiceOrder).where(
                    ServiceOrder.tenant_id == owner_tid,
                    or_(
                        ServiceOrder.company_id == company_id_str,
                        ServiceOrder.customer_id == company_id_str,
                    ),
                )
            )
        )
        .scalars()
        .all()
    )


def filter_active_orders(orders: list[ServiceOrder]) -> list[ServiceOrder]:
    return [
        o
        for o in orders
        if str(getattr(o, "status", "") or "").lower() not in CLIENT_ACTIVE_ORDER_EXCLUDED_STATUSES
    ]


def billable_order_ids(active_orders: list[ServiceOrder]) -> list[str]:
    return [
        str(o.id)
        for o in active_orders
        if str(getattr(o, "status", "") or "").lower() in CLIENT_BILLABLE_ORDER_STATUSES
    ]


async def invoiced_order_ids(
    db: AsyncSession,
    order_ids: list[str],
) -> set[str]:
    if not order_ids:
        return set()
    rows = (
        await db.execute(
            select(Invoice.service_order_id, Invoice.status).where(
                Invoice.service_order_id.in_(order_ids)
            )
        )
    ).all()
    out: set[str] = set()
    for order_id, inv_status in rows:
        if str(inv_status or "").lower() not in CLIENT_INVOICE_VOID_STATUSES:
            out.add(str(order_id))
    return out


async def client_has_any_invoice(
    db: AsyncSession,
    active_orders: list[ServiceOrder],
) -> bool:
    order_ids = [str(o.id) for o in active_orders]
    if not order_ids:
        return False
    return bool(await invoiced_order_ids(db, order_ids))


async def billable_orders_missing_invoice(
    db: AsyncSession,
    active_orders: list[ServiceOrder],
) -> bool:
    billable = billable_order_ids(active_orders)
    if not billable:
        return False
    invoiced = await invoiced_order_ids(db, billable)
    return any(oid not in invoiced for oid in billable)


def _order_created_ts(order: ServiceOrder) -> Any:
    created = getattr(order, "created_at", None)
    return created if created is not None else ""


async def resolve_client_open_order(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> Optional[ServiceOrder]:
    """The newest order a new service line can be appended to.

    "Editable" = status draft/confirmed, not completed/cancelled/in-progress,
    and not already invoiced. Returns None when the client has no such order
    (the caller then opens a fresh Service Order).
    """
    orders = await fetch_client_orders(db, tenant_id=tenant_id, company_id=company_id)
    editable = [
        o
        for o in orders
        if str(getattr(o, "status", "") or "").lower() in CLIENT_EDITABLE_ORDER_STATUSES
    ]
    if not editable:
        return None
    invoiced = await invoiced_order_ids(db, [str(o.id) for o in editable])
    candidates = [o for o in editable if str(o.id) not in invoiced]
    if not candidates:
        return None
    candidates.sort(key=_order_created_ts, reverse=True)
    return candidates[0]


async def add_client_service_items(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    own_company_id: Optional[str],
    items: Sequence[dict[str, Any]],
    requested_by: Optional[str] = None,
    source: str = "client_workspace_add_service",
    extra_audit: Optional[dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> ServiceOrder:
    """Sell one or more catalog services to an existing client.

    Single money contour for first and Nth sale: append to the client's open
    editable order when one exists, otherwise create the first Service Order.
    Does not commit — the caller owns the transaction boundary.
    """
    from backend.app.services.additional_services import AdditionalServicesService

    svc = AdditionalServicesService(db, str(tenant_id))
    items_payload: list[dict[str, Any]] = [
        {
            "service_id": str(it.get("service_id")),
            "qty": it.get("qty", 1),
            "beneficiary_kind": it.get("beneficiary_kind"),
            "beneficiary_id": it.get("beneficiary_id"),
        }
        for it in items
    ]

    order = await resolve_client_open_order(
        db, tenant_id=str(tenant_id), company_id=str(company_id)
    )
    audit = {"source": source, "company_id": str(company_id)}
    if extra_audit:
        audit.update(extra_audit)

    if order is None:
        order = await svc.create_order(
            {
                "company_id": str(company_id),
                "own_company_id": str(own_company_id) if own_company_id else None,
                "currency": "PLN",
                "notes": notes or "",
                "requested_by": requested_by or "",
                "audit": audit,
            },
            items_payload,
        )
    else:
        for item_payload in items_payload:
            await svc.add_item(order, item_payload)

    return order
