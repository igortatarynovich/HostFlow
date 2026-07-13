#!/usr/bin/env python3
"""Path 4: Meta B2B "Targeting" inquiry → Client → Service Order (Targeting) → Invoice.

Scenario (Service Inquiry, NOT recruitment):
  Meta form/ad "Targeting" → Inquiry → Sales → Client → Service Order
    customer   = Client (Bill-To)
    beneficiary = Client (service is for the client's own company)
    service item = Targeting (inline execution now, handoff to Marketing later)
  → fulfill → invoice billed to the Client.

Uses a real converted Meta B2B client_lead (Essa → MROZEK TRANSPORT).
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app import models as _models  # noqa: F401,E402
from backend.app.models import _load_model_module  # noqa: E402

_load_model_module("workforce_zus_workspace_task")
_load_model_module("workforce_tax_profile")

from sqlalchemy import select  # noqa: E402

from backend.app.api.v1.invoices import crud as invoice_crud  # noqa: E402
from backend.app.core.settings import settings  # noqa: F401,E402
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.additional_service import Service, ServiceOrderStatus  # noqa: E402
from backend.app.models.company import Company  # noqa: E402
from backend.app.models.invoice import InvoiceStatus  # noqa: E402
from backend.app.models.lead import Lead  # noqa: E402
from backend.app.schemas.additional_services import ServiceOrderOut  # noqa: E402
from backend.app.services.additional_services import AdditionalServicesService  # noqa: E402
from backend.app.services.service_order_beneficiary import (  # noqa: E402
    resolve_customer,
    resolve_item_beneficiary,
)
from backend.app.services.service_order_invoice_billing import (  # noqa: E402
    build_service_order_invoice_billing,
)

TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"
OWN_COMPANY_ID = "4f91ce01-f909-4d79-8a83-679c9eae1b78"
USER_ID = "b97c3ee4-d0e5-429f-ab1d-762fc518363b"
# Real converted Meta B2B client lead + its client company (MROZEK TRANSPORT).
SAMPLE_LEAD_ID = "2220c7a9-ee29-418d-9a3f-7b9d96834e5e"
CLIENT_ID = "c17d9487-eedf-4333-aeb6-e446357ce570"

SERVICE_CODE = "targeting_ads"
SERVICE_NAME = "Таргетированная реклама (Targeting)"


def step(msg: str, data: dict | None = None) -> None:
    print(f"\n=== {msg} ===")
    if data is not None:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


async def ensure_targeting_service(svc: AdditionalServicesService) -> Service:
    """Targeting service: inline execution now, handoff to Marketing later."""
    try:
        return await svc.get_service_by_code(SERVICE_CODE)
    except Exception:
        return await svc.create_service(
            {
                "code": SERVICE_CODE,
                "name": SERVICE_NAME,
                "category": "marketing",
                "base_price": Decimal("2000.00"),
                "estimated_cost": Decimal("500.00"),
                "cost_currency": "PLN",
                "currency": "PLN",
                "vat_rate": Decimal("23"),
                "unit": "package",
                "requires_schedule": False,
                "requires_candidate": False,
                "is_active": True,
                # Inline for now. To route to Marketing later, switch meta to:
                #   {"execution": {"mode": "handoff", "handoff_action": "marketing.create_project"}}
                "meta": {"execution": {"mode": "inline"}, "execution_mode": "inline", "blocking": False},
            }
        )


async def main() -> int:
    results: list[tuple[str, str]] = []

    async with async_session_maker() as db:
        # 1. Meta B2B client lead → converted client (Sales outcome)
        lead = (
            await db.execute(
                select(Lead).where(Lead.id == SAMPLE_LEAD_ID, Lead.tenant_id == TENANT_ID).limit(1)
            )
        ).scalar_one_or_none()
        if not lead:
            step("FAIL step 1", {"error": "sample Meta client_lead not found"})
            return 1
        if not str(getattr(lead, "converted_client_id", "") or "").strip():
            lead.converted_client_id = CLIENT_ID
            lead.stage = "converted"
            lead.status = "processed"
        normalized = dict(lead.normalized or {})
        # Reset any prior order link so the scenario is repeatable.
        normalized.pop("service_order_id", None)
        normalized.pop("service_order_created_at", None)
        normalized["converted_client_id"] = lead.converted_client_id
        lead.normalized = normalized
        await db.flush()

        company = await db.get(Company, CLIENT_ID)
        step(
            "1. Meta B2B inquiry → Client",
            {
                "lead_id": lead.id,
                "source": lead.source,
                "meta_source": {
                    "form_id": normalized.get("form_id") or (normalized.get("meta") or {}).get("form_id"),
                    "ad_id": normalized.get("ad_id") or (normalized.get("meta") or {}).get("ad_id"),
                    "campaign_id": normalized.get("campaign_id")
                    or (normalized.get("meta") or {}).get("campaign_id"),
                },
                "client_id": lead.converted_client_id,
                "client_name": getattr(company, "name", None),
            },
        )
        results.append(("1_inquiry_to_client", "PASS" if company else "FAIL"))

        # 2. Catalog: Targeting service (inline)
        svc = AdditionalServicesService(db, TENANT_ID)
        service = await ensure_targeting_service(svc)
        await db.flush()
        step(
            "2. Catalog: Targeting service",
            {
                "id": service.id,
                "code": service.code,
                "name": service.name,
                "base_price": str(service.base_price),
                "execution": (service.meta or {}).get("execution"),
            },
        )
        results.append(("2_catalog_targeting", "PASS"))

        # 3. Service Order: customer = Client, beneficiary = Client, item = Targeting
        order = await svc.create_order(
            {
                "company_id": CLIENT_ID,
                "own_company_id": OWN_COMPANY_ID,
                "currency": "PLN",
                "notes": f"Path 4 Targeting service inquiry · lead {lead.id}",
                "requested_by": USER_ID,
                "audit": {"source": "client_lead_service_order", "lead_id": str(lead.id), "route": "service_inquiry"},
            },
            [{"service_id": str(service.id), "qty": Decimal("1")}],
        )
        normalized["service_order_id"] = str(order.id)
        lead.normalized = normalized
        await db.flush()

        order = await svc.get_order(order.id)
        out = ServiceOrderOut.model_validate(order, from_attributes=True)
        cust_kind, cust_id = resolve_customer(order)
        item0 = order.items[0]
        ben_kind, ben_id = resolve_item_beneficiary(item0, order)
        step(
            "3. Service Order (Targeting)",
            {
                "order_id": out.id,
                "customer_kind": out.customer_kind,
                "customer_id": out.customer_id,
                "resolved_customer": [cust_kind, cust_id],
                "line_beneficiary": [ben_kind, ben_id],
                "items": [
                    {"code": i.service_code or i.service_id, "execution_mode": i.execution_mode, "amount": str(i.amount)}
                    for i in out.items
                ],
                "total_amount": str(out.total_amount),
            },
        )
        order_ok = (
            cust_kind == "client"
            and cust_id == CLIENT_ID
            and ben_kind == "client"
            and ben_id == CLIENT_ID
            and len(out.items) == 1
            and out.items[0].execution_mode == "inline"
            and Decimal(str(out.total_amount)) > 0
        )
        results.append(("3_service_order", "PASS" if order_ok else "FAIL"))

        # 4. Fulfillment: confirm → in_progress → deliver → completed
        order = await svc.set_order_status(order, ServiceOrderStatus.confirmed.value)
        order = await svc.set_order_status(order, ServiceOrderStatus.in_progress.value)
        item = await svc.get_item(item0.id)
        item = await svc.deliver_item(item)
        order = await svc.get_order(order.id)
        order = await svc.set_order_status(order, ServiceOrderStatus.completed.value)
        step("4. Fulfillment", {"order_status": order.status, "item_status": item.status})
        results.append(("4_fulfillment", "PASS" if order.status == ServiceOrderStatus.completed.value else "FAIL"))
        await db.commit()

        # 5. Invoice — billed to the Client (Bill-To customer)
        order = await svc.get_order(order.id)
        issue_date = date.today()
        due_date = issue_date + timedelta(days=14)
        items_payload = [
            {
                "line_no": idx,
                "description": getattr(getattr(line, "service", None), "name", None) or SERVICE_NAME,
                "qty": line.qty,
                "unit_price": line.unit_price,
                "vat_rate": line.vat_rate,
            }
            for idx, line in enumerate(order.items, start=1)
        ]
        billing_details = build_service_order_invoice_billing(company=company, candidate=None, employee=None)
        invoice = await invoice_crud.create_invoice(
            db,
            TENANT_ID,
            {
                "own_company_id": OWN_COMPANY_ID,
                "company_id": CLIENT_ID,
                "service_order_id": order.id,
                "issue_date": issue_date,
                "due_date": due_date,
                "currency": order.currency or "PLN",
                "status": InvoiceStatus.draft.value,
                "items": items_payload,
                "billing_details": billing_details,
                "notes": order.notes,
            },
            created_by=USER_ID,
        )
        await db.commit()
        step(
            "5. Invoice (billed to Client)",
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "company_id": invoice.company_id,
                "service_order_id": invoice.service_order_id,
                "total_amount": str(invoice.total_amount),
                "billing_company": billing_details.get("company_name"),
                "billing_tax_id": billing_details.get("tax_id"),
                "status": invoice.status,
            },
        )
        invoice_ok = (
            invoice.company_id == CLIENT_ID
            and invoice.service_order_id == order.id
            and Decimal(str(invoice.total_amount or 0)) > 0
            and bool(billing_details.get("company_name"))
        )
        results.append(("5_invoice_billed_client", "PASS" if invoice_ok else "FAIL"))

    step("SUMMARY", {k: v for k, v in results})
    failed = [k for k, v in results if v == "FAIL"]
    if failed:
        print(f"\nPATH 4: FAIL ({', '.join(failed)})", file=sys.stderr)
        return 1
    print("\nPATH 4: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
