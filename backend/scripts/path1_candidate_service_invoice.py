#!/usr/bin/env python3
"""Path 1 staging check: Candidate → Service Order → Completed → Invoice."""
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

from sqlalchemy import select

from backend.app import models as _models  # noqa: F401
from backend.app.models import _load_model_module

_load_model_module("workforce_zus_workspace_task")  # WorkforceEmployee relationship
_load_model_module("workforce_tax_profile")
from backend.app.api.v1.invoices import crud as invoice_crud
from backend.app.core.settings import settings  # noqa: F401
from backend.app.db.session import async_session_maker
from backend.app.models.additional_service import Service, ServiceOrderStatus
from backend.app.models.candidate import Candidate
from backend.app.models.invoice import InvoiceStatus
from backend.app.schemas.additional_services import ServiceOrderOut
from backend.app.services.additional_services import AdditionalServicesService
from backend.app.services.service_order_invoice_billing import build_service_order_invoice_billing


TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"
CANDIDATE_ID = "5d41ce61-4adc-48d4-899b-0d7f462762dc"
OWN_COMPANY_ID = "4f91ce01-f909-4d79-8a83-679c9eae1b78"
USER_ID = "b97c3ee4-d0e5-429f-ab1d-762fc518363b"
SERVICE_CODE = "karta_pobyta"
SERVICE_NAME = "Karta pobyta"


def step(msg: str, data: dict | None = None) -> None:
    print(f"\n=== {msg} ===")
    if data is not None:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


async def ensure_catalog_service(svc: AdditionalServicesService) -> Service:
    try:
        return await svc.get_service_by_code(SERVICE_CODE)
    except Exception:
        pass
    service = await svc.create_service(
        {
            "code": SERVICE_CODE,
            "name": SERVICE_NAME,
            "category": "legal",
            "base_price": Decimal("450.00"),
            "estimated_cost": Decimal("120.00"),
            "cost_currency": "PLN",
            "currency": "PLN",
            "vat_rate": Decimal("23"),
            "unit": "piece",
            "requires_schedule": False,
            "requires_candidate": True,
            "is_active": True,
            "meta": {"execution": "inline", "blocking": False},
        }
    )
    return service


async def main() -> int:
    results: list[tuple[str, str]] = []

    async with async_session_maker() as db:
        svc = AdditionalServicesService(db, TENANT_ID)

        # 1. Candidate
        cand = (
            await db.execute(
                select(Candidate).where(
                    Candidate.id == CANDIDATE_ID,
                    Candidate.tenant_id == TENANT_ID,
                    Candidate.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not cand:
            step("FAIL step 1", {"error": "candidate not found"})
            return 1
        step(
            "1. Candidate",
            {
                "id": cand.id,
                "name": f"{cand.first_name} {cand.last_name}",
                "email": cand.email,
            },
        )
        results.append(("1_candidate", "PASS"))

        # 2. Catalog service
        service = await ensure_catalog_service(svc)
        await db.flush()
        step(
            "2. Catalog service",
            {
                "id": service.id,
                "code": service.code,
                "name": service.name,
                "execution": (service.meta or {}).get("execution"),
            },
        )
        results.append(("2_catalog", "PASS"))

        # 3. Create order (beneficiary = candidate)
        order = await svc.create_order(
            {
                "candidate_id": CANDIDATE_ID,
                "own_company_id": OWN_COMPANY_ID,
                "requested_by": USER_ID,
                "currency": "PLN",
                "notes": "Path 1 staging verification",
            },
            [{"service_id": service.id, "qty": 1}],
        )
        await db.flush()
        order = await svc.get_order(order.id)
        out = ServiceOrderOut.model_validate(order, from_attributes=True)
        step(
            "3. Service order created",
            {
                "order_id": out.id,
                "status": out.status,
                "beneficiary_kind": out.beneficiary_kind,
                "beneficiary_id": out.beneficiary_id,
                "candidate_id": out.candidate_id,
                "items": [
                    {
                        "id": i.id,
                        "status": i.status,
                        "execution_mode": i.execution_mode,
                    }
                    for i in out.items
                ],
            },
        )
        if out.beneficiary_kind != "candidate" or out.beneficiary_id != CANDIDATE_ID:
            results.append(("3_beneficiary", "FAIL"))
            await db.rollback()
            return 1
        results.append(("3_beneficiary", "PASS"))

        item = order.items[0]

        # 4. Confirm → in_progress → deliver → completed
        order = await svc.set_order_status(order, ServiceOrderStatus.confirmed.value)
        step("4a. Confirmed", {"status": order.status})

        order = await svc.set_order_status(order, ServiceOrderStatus.in_progress.value)
        step("4b. In progress", {"status": order.status})

        item = await svc.get_item(item.id)
        item = await svc.deliver_item(item)
        step("4c. Item delivered", {"item_status": item.status})

        order = await svc.get_order(order.id)
        order = await svc.set_order_status(order, ServiceOrderStatus.completed.value)
        step("4d. Completed", {"status": order.status})
        results.append(("4_fulfillment", "PASS"))

        await db.commit()

        # 5. Invoice from service order
        order = await svc.get_order(order.id)
        candidate = cand
        issue_date = date.today()
        due_date = issue_date + timedelta(days=14)
        items_payload = []
        for idx, line in enumerate(order.items, start=1):
            service_name = getattr(getattr(line, "service", None), "name", None)
            items_payload.append(
                {
                    "line_no": idx,
                    "description": service_name or SERVICE_NAME,
                    "qty": line.qty,
                    "unit_price": line.unit_price,
                    "vat_rate": line.vat_rate,
                }
            )

        billing_details = build_service_order_invoice_billing(company=None, candidate=candidate)

        invoice = await invoice_crud.create_invoice(
            db,
            TENANT_ID,
            {
                "own_company_id": OWN_COMPANY_ID,
                "candidate_id": CANDIDATE_ID,
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
            "5. Invoice created",
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "candidate_id": invoice.candidate_id,
                "service_order_id": invoice.service_order_id,
                "total_amount": str(invoice.total_amount),
                "status": invoice.status,
            },
        )
        results.append(("5_invoice", "PASS"))

        # 6. Closure check (UI heuristic: completed + invoice + no outstanding = closed)
        inv_summary = {
            "invoice_id": invoice.id,
            "status": invoice.status,
            "total_amount": float(invoice.total_amount or 0),
            "paid_amount": float(invoice.paid_amount or 0),
        }
        outstanding = max(
            0,
            float(invoice.total_amount or 0) - float(invoice.paid_amount or 0),
        )
        order_final = await svc.get_order(order.id)
        next_action = "invoice_needed"
        if order_final.status == ServiceOrderStatus.completed.value and invoice.id:
            if outstanding > 0 and str(invoice.status).lower() not in ("paid", "cancelled"):
                next_action = "collect_payment"
            else:
                next_action = "closed" if outstanding <= 0 else "collect_payment"

        step(
            "6. Order closure",
            {
                "order_status": order_final.status,
                "item_statuses": [i.status for i in order_final.items],
                "invoice_linked": bool(invoice.service_order_id == order_final.id),
                "next_action": next_action,
            },
        )
        closure_ok = (
            order_final.status == ServiceOrderStatus.completed.value
            and invoice.service_order_id == order_final.id
            and next_action in ("collect_payment", "closed")
        )
        results.append(("6_closure", "PASS" if closure_ok else "FAIL"))

    step("SUMMARY", {k: v for k, v in results})
    failed = [k for k, v in results if v == "FAIL"]
    if failed:
        print(f"\nPATH 1: FAIL ({', '.join(failed)})", file=sys.stderr)
        return 1
    print("\nPATH 1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
