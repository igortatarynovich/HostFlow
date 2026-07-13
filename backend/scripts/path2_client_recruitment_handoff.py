#!/usr/bin/env python3
"""Path 2 staging check: Client → Service Order (recruitment item) → Handoff → Create Search.

Validates the order-line → executor contract (the "Services bridge"):
  - beneficiary = client
  - item.execution_mode = handoff, handoff_action = recruitment.create_search
  - platform completion resolves the recruitment handoff for this order line
"""
from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app import models as _models  # noqa: F401
from backend.app.models import _load_model_module

_load_model_module("workforce_zus_workspace_task")
_load_model_module("workforce_tax_profile")

from sqlalchemy import select  # noqa: E402

from backend.app.core.settings import settings  # noqa: F401,E402
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.additional_service import Service, ServiceOrderStatus  # noqa: E402
from backend.app.models.company import Company  # noqa: E402
from backend.app.schemas.additional_services import ServiceOrderOut  # noqa: E402
from backend.app.services.additional_services import AdditionalServicesService  # noqa: E402
from backend.app.services.platform_completion_service import (  # noqa: E402
    SERVICES_ORDER_COMPLETED,
    resolve_platform_completion,
)

TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"
OWN_COMPANY_ID = "4f91ce01-f909-4d79-8a83-679c9eae1b78"
USER_ID = "b97c3ee4-d0e5-429f-ab1d-762fc518363b"
CLIENT_COMPANY_ID = "c17d9487-eedf-4333-aeb6-e446357ce570"  # MROZEK TRANSPORT (client)
SERVICE_CODE = "recruitment_search"
SERVICE_NAME = "Подбор персонала (recruitment)"
HANDOFF_ACTION = "recruitment.create_search"


def step(msg: str, data: dict | None = None) -> None:
    print(f"\n=== {msg} ===")
    if data is not None:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


async def ensure_recruitment_service(svc: AdditionalServicesService) -> Service:
    try:
        existing = await svc.get_service_by_code(SERVICE_CODE)
        # Make sure execution meta is present (idempotent repair).
        meta = dict(existing.meta or {})
        if not isinstance(meta.get("execution"), dict):
            meta["execution"] = {"mode": "handoff", "handoff_action": HANDOFF_ACTION}
            meta["execution_mode"] = "handoff"
            meta["handoff_action"] = HANDOFF_ACTION
            await svc.update_service(existing, {"meta": meta})
        return existing
    except Exception:
        pass
    return await svc.create_service(
        {
            "code": SERVICE_CODE,
            "name": SERVICE_NAME,
            "category": "recruitment",
            "base_price": Decimal("0"),
            "estimated_cost": Decimal("0"),
            "cost_currency": "PLN",
            "currency": "PLN",
            "vat_rate": Decimal("23"),
            "unit": "package",
            "requires_schedule": False,
            "requires_candidate": False,
            "is_active": True,
            "meta": {
                "execution": {"mode": "handoff", "handoff_action": HANDOFF_ACTION},
                "execution_mode": "handoff",
                "handoff_action": HANDOFF_ACTION,
                "blocking": False,
            },
        }
    )


async def main() -> int:
    results: list[tuple[str, str]] = []

    async with async_session_maker() as db:
        svc = AdditionalServicesService(db, TENANT_ID)

        # 1. Client company
        client = (
            await db.execute(
                select(Company).where(
                    Company.id == CLIENT_COMPANY_ID,
                    Company.tenant_id == TENANT_ID,
                )
            )
        ).scalar_one_or_none()
        if not client:
            step("FAIL step 1", {"error": "client company not found"})
            return 1
        step("1. Client company", {"id": client.id, "name": client.name})
        results.append(("1_client", "PASS"))

        # 2. Catalog service (recruitment, execution=handoff)
        service = await ensure_recruitment_service(svc)
        await db.flush()
        step(
            "2. Recruitment catalog service",
            {
                "id": service.id,
                "code": service.code,
                "meta": service.meta,
            },
        )
        results.append(("2_catalog", "PASS"))

        # 3. Create client service order with the recruitment (handoff) item
        order = await svc.create_order(
            {
                "company_id": CLIENT_COMPANY_ID,
                "own_company_id": OWN_COMPANY_ID,
                "requested_by": USER_ID,
                "currency": "PLN",
                "notes": "Path 2 staging verification (recruitment handoff)",
            },
            [{"service_id": service.id, "qty": 1}],
        )
        await db.flush()
        order = await svc.get_order(order.id)
        out = ServiceOrderOut.model_validate(order, from_attributes=True)
        item_out = out.items[0]
        step(
            "3. Client service order created",
            {
                "order_id": out.id,
                "status": out.status,
                "beneficiary_kind": out.beneficiary_kind,
                "beneficiary_id": out.beneficiary_id,
                "company_id": out.company_id,
                "item": {
                    "id": item_out.id,
                    "execution_mode": item_out.execution_mode,
                    "handoff_action": item_out.handoff_action,
                },
            },
        )
        contract_ok = (
            out.beneficiary_kind == "client"
            and out.beneficiary_id == CLIENT_COMPANY_ID
            and item_out.execution_mode == "handoff"
            and item_out.handoff_action == HANDOFF_ACTION
        )
        results.append(("3_line_contract", "PASS" if contract_ok else "FAIL"))
        await db.commit()

        # 4. Platform resolves recruitment handoff for this order line
        resolution = await resolve_platform_completion(
            db,
            TENANT_ID,
            event=SERVICES_ORDER_COMPLETED,
            context={
                "service_order_id": order.id,
                "client_id": CLIENT_COMPANY_ID,
                "client_name": client.name,
            },
        )
        handoff_actions = [h.get("action") for h in (resolution.get("handoffs") or [])]
        step(
            "4. Platform completion → executor launch",
            {
                "handoffs": resolution.get("handoffs"),
                "primary_handoff": resolution.get("handoff"),
            },
        )
        resolve_ok = HANDOFF_ACTION in handoff_actions
        results.append(("4_platform_handoff", "PASS" if resolve_ok else "FAIL"))

    step("SUMMARY", {k: v for k, v in results})
    failed = [k for k, v in results if v == "FAIL"]
    if failed:
        print(f"\nPATH 2: FAIL ({', '.join(failed)})", file=sys.stderr)
        return 1
    print("\nPATH 2: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
