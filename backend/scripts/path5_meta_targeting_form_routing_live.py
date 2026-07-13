#!/usr/bin/env python3
"""Path 5: Live Meta Targeting form routing on hanging leads.

Configures form_id → Service Inquiry (targeting_ads), reprocesses needs_routing
leads, then runs Sales → Client → Service Order → Invoice.

PASS criteria:
  - leads leave needs_routing / AD_NOT_MAPPED
  - appear as processed client_lead in Sales
  - normalized.service_inquiry_v1.service_code = targeting_ads
  - Service Order: customer=client, beneficiary=client, item=targeting_ads, inline
  - fulfill + invoice billed to client
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
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.additional_service import ServiceOrderStatus  # noqa: E402
from backend.app.models.invoice import InvoiceStatus  # noqa: E402
from backend.app.models.lead import Lead  # noqa: E402
from backend.app.modules.leads import crud as leads_crud  # noqa: E402
from backend.app.modules.leads.admin_service import retry_leads  # noqa: E402
from backend.app.modules.leads.lead_client_conversion import create_client_from_lead_conversion  # noqa: E402
from backend.app.modules.leads.schemas import MetaLeadRetryRequest  # noqa: E402
from backend.app.schemas.additional_services import ServiceOrderOut  # noqa: E402
from backend.app.services.additional_services import AdditionalServicesService  # noqa: E402
from backend.app.services.service_order_beneficiary import (  # noqa: E402
    resolve_customer,
    resolve_item_beneficiary,
)
from backend.app.services.service_order_invoice_billing import build_service_order_invoice_billing  # noqa: E402

TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"
OWN_COMPANY_ID = "4f91ce01-f909-4d79-8a83-679c9eae1b78"
USER_ID = "b97c3ee4-d0e5-429f-ab1d-762fc518363b"

# Real Targeting Meta form + the one hanging lead (Karol / Waldemar sp zoo).
TARGET_FORM_ID = "1917672235588961"
TARGET_PAGE_ID = "754105441119579"
HANGING_LEAD_ID = "4cb9faa3-cf19-40c7-b370-4adb092023aa"

SERVICE_CODE = "targeting_ads"
SERVICE_NAME = "Таргетированная реклама (Targeting)"


def step(msg: str, data: dict | None = None) -> None:
    print(f"\n=== {msg} ===")
    if data is not None:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


async def ensure_targeting_service(svc: AdditionalServicesService):
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
                "meta": {"execution": {"mode": "inline"}, "execution_mode": "inline", "blocking": False},
            }
        )


async def main() -> int:
    results: list[tuple[str, str]] = []

    async with async_session_maker() as db:
        # 0. Configure form route: Service Inquiry + targeting_ads
        route = await leads_crud.upsert_meta_form_route(
            db,
            tenant_id=TENANT_ID,
            form_id=TARGET_FORM_ID,
            own_company_id=OWN_COMPANY_ID,
            lead_target_type="service_order_lead",
            page_id=TARGET_PAGE_ID,
            source="meta",
            service_code=SERVICE_CODE,
            is_active=True,
            updated_by="path5_script",
        )
        await db.commit()
        step(
            "0. Form route configured",
            {
                "form_id": route.form_id,
                "lead_target_type": route.lead_target_type,
                "service_code": route.service_code,
                "own_company_id": route.own_company_id,
            },
        )
        results.append(("0_form_route", "PASS" if route.service_code == SERVICE_CODE else "FAIL"))

        # 1. Reprocess hanging lead(s) for this form
        retry_result = await retry_leads(
            db,
            TENANT_ID,
            OWN_COMPANY_ID,
            MetaLeadRetryRequest(lead_ids=[HANGING_LEAD_ID], refresh_graph=False),
        )
        await db.commit()
        item = retry_result.items[0] if retry_result.items else None
        step(
            "1. Reprocess hanging lead",
            {
                "processed": retry_result.processed,
                "item": item.model_dump() if item else None,
            },
        )

        lead = (
            await db.execute(
                select(Lead).where(Lead.id == HANGING_LEAD_ID, Lead.tenant_id == TENANT_ID).limit(1)
            )
        ).scalar_one_or_none()
        if not lead:
            print("FAIL: lead not found after retry")
            return 1

        normalized = dict(lead.normalized or {})
        svc_inquiry = normalized.get("service_inquiry_v1") or {}
        route_v1 = normalized.get("intake_route_v1") or {}
        reprocess_ok = (
            lead.status == "processed"
            and not lead.error
            and svc_inquiry.get("service_code") == SERVICE_CODE
            and route_v1.get("route_intent") == "service_request"
        )
        step(
            "1b. Lead state after reprocess",
            {
                "id": lead.id,
                "status": lead.status,
                "error": lead.error,
                "lead_type": lead.lead_type,
                "lead_target_type": lead.lead_target_type,
                "service_inquiry_v1": svc_inquiry,
                "intake_route_v1": route_v1,
            },
        )
        results.append(("1_reprocess", "PASS" if reprocess_ok else "FAIL"))

        # 2. Convert to Client (Sales outcome)
        normalized.pop("service_order_id", None)
        normalized.pop("service_order_created_at", None)
        lead.normalized = normalized
        lead.converted_client_id = None
        await db.flush()

        client, idempotent = await create_client_from_lead_conversion(
            db,
            tenant_id=TENANT_ID,
            lead=lead,
            normalized=normalized,
            source_channel="meta",
            conversion_reason="path5_targeting_form_routing",
        )
        await db.commit()
        step(
            "2. Convert to Client",
            {
                "client_id": str(client.id),
                "client_name": client.name,
                "idempotent_replay": idempotent,
                "converted_client_id": lead.converted_client_id,
            },
        )
        results.append(("2_client", "PASS" if lead.converted_client_id else "FAIL"))

        # 3. Service Order with targeting_ads (customer=client, beneficiary=client)
        svc = AdditionalServicesService(db, TENANT_ID)
        service = await ensure_targeting_service(svc)
        await db.flush()

        # Simulate UI preselect from service_inquiry_v1
        preselect_code = (normalized.get("service_inquiry_v1") or {}).get("service_code")
        assert preselect_code == SERVICE_CODE, f"preselect mismatch: {preselect_code}"

        order = await svc.create_order(
            {
                "company_id": str(client.id),
                "own_company_id": OWN_COMPANY_ID,
                "currency": "PLN",
                "notes": f"Path 5 Targeting form routing · lead {lead.id}",
                "requested_by": USER_ID,
                "audit": {
                    "source": "client_lead_service_order",
                    "lead_id": str(lead.id),
                    "service_inquiry_v1": normalized.get("service_inquiry_v1"),
                },
            },
            [{"service_id": str(service.id), "qty": Decimal("1")}],
        )
        normalized["service_order_id"] = str(order.id)
        lead.normalized = normalized
        await db.commit()

        order = await svc.get_order(order.id)
        out = ServiceOrderOut.model_validate(order, from_attributes=True)
        cust_kind, cust_id = resolve_customer(order)
        item0 = order.items[0]
        ben_kind, ben_id = resolve_item_beneficiary(item0, order)
        step(
            "3. Service Order",
            {
                "order_id": out.id,
                "preselected_service_code": preselect_code,
                "customer": [cust_kind, cust_id],
                "beneficiary": [ben_kind, ben_id],
                "items": [
                    {
                        "service_code": i.service_code,
                        "execution_mode": i.execution_mode,
                        "amount": str(i.amount),
                    }
                    for i in out.items
                ],
            },
        )
        order_ok = (
            cust_kind == "client"
            and cust_id == str(client.id)
            and ben_kind == "client"
            and ben_id == str(client.id)
            and len(out.items) == 1
            and (out.items[0].service_code == SERVICE_CODE or item0.service_code == SERVICE_CODE)
            and out.items[0].execution_mode == "inline"
        )
        results.append(("3_service_order", "PASS" if order_ok else "FAIL"))

        # 4. Fulfillment
        order = await svc.set_order_status(order, ServiceOrderStatus.confirmed.value)
        order = await svc.set_order_status(order, ServiceOrderStatus.in_progress.value)
        item = await svc.deliver_item(await svc.get_item(item0.id))
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
        billing_details = build_service_order_invoice_billing(company=client, candidate=None, employee=None)
        invoice = await invoice_crud.create_invoice(
            db,
            TENANT_ID,
            {
                "own_company_id": OWN_COMPANY_ID,
                "company_id": str(client.id),
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
            "5. Invoice",
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "company_id": invoice.company_id,
                "service_order_id": invoice.service_order_id,
                "total": str(invoice.total_amount),
                "status": invoice.status,
            },
        )
        results.append(("5_invoice", "PASS" if str(invoice.company_id) == str(client.id) else "FAIL"))

    print("\n=== SUMMARY ===")
    all_pass = True
    for name, status in results:
        print(f"  {name}: {status}")
        if status != "PASS":
            all_pass = False
    print("\nOVERALL:", "PASS" if all_pass else "FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
