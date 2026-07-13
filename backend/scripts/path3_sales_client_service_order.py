#!/usr/bin/env python3
"""Path 3: Sales → Service Order bridge (client_lead with catalog lines)."""
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
from backend.app.models.additional_service import Service  # noqa: E402
from backend.app.models.lead import Lead  # noqa: E402
from backend.app.schemas.additional_services import ServiceOrderOut  # noqa: E402
from backend.app.services.additional_services import AdditionalServicesService  # noqa: E402

TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"
CLIENT_ID = "c17d9487-eedf-4333-aeb6-e446357ce570"
SAMPLE_LEAD_ID = "2220c7a9-ee29-418d-9a3f-7b9d96834e5e"


def step(msg: str, data: dict | None = None) -> None:
    print(f"\n=== {msg} ===")
    if data is not None:
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


async def find_sample_client_lead(db) -> Lead | None:
    stmt = select(Lead).where(Lead.id == SAMPLE_LEAD_ID, Lead.tenant_id == TENANT_ID).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def ensure_inline_service(svc: AdditionalServicesService) -> Service:
    code = "karta_pobyta"
    try:
        return await svc.get_service_by_code(code)
    except Exception:
        return await svc.create_service(
            {
                "code": code,
                "name": "Karta pobyta",
                "category": "legal",
                "base_price": Decimal("450"),
                "estimated_cost": Decimal("120"),
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


async def ensure_handoff_service(svc: AdditionalServicesService) -> Service:
    code = "recruitment_search"
    try:
        return await svc.get_service_by_code(code)
    except Exception:
        return await svc.create_service(
            {
                "code": code,
                "name": "Подбор персонала",
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
                    "execution": {"mode": "handoff", "handoff_action": "recruitment.create_search"},
                    "execution_mode": "handoff",
                    "handoff_action": "recruitment.create_search",
                },
            }
        )


async def ensure_b2b_inline_service(svc: AdditionalServicesService) -> Service:
    code = "b2b_onboarding"
    try:
        return await svc.get_service_by_code(code)
    except Exception:
        return await svc.create_service(
            {
                "code": code,
                "name": "Онбординг клиента",
                "category": "sales",
                "base_price": Decimal("500"),
                "estimated_cost": Decimal("100"),
                "cost_currency": "PLN",
                "currency": "PLN",
                "vat_rate": Decimal("23"),
                "unit": "package",
                "requires_schedule": False,
                "requires_candidate": False,
                "is_active": True,
                "meta": {"execution": "inline", "blocking": False},
            }
        )


async def main() -> int:
    results: list[tuple[str, str]] = []

    async with async_session_maker() as db:
        lead = await find_sample_client_lead(db)
        if not lead:
            step("FAIL", {"error": "sample client_lead not found"})
            return 1
        if not str(getattr(lead, "converted_client_id", "") or "").strip():
            lead.converted_client_id = CLIENT_ID
            lead.stage = "converted"
            lead.status = "processed"
            normalized = dict(lead.normalized or {})
            normalized["converted_client_id"] = CLIENT_ID
            lead.normalized = normalized
            await db.flush()
        step(
            "1. Client lead (sales)",
            {"lead_id": lead.id, "client_id": lead.converted_client_id},
        )
        results.append(("1_lead", "PASS"))

        svc = AdditionalServicesService(db, TENANT_ID)
        inline = await ensure_b2b_inline_service(svc)
        handoff = await ensure_handoff_service(svc)
        await db.flush()
        step("2. Catalog", {"inline": inline.code, "handoff": handoff.code})
        results.append(("2_catalog", "PASS"))

        normalized = dict(lead.normalized or {})
        normalized.pop("service_order_id", None)
        normalized.pop("service_order_created_at", None)
        lead.normalized = normalized
        await db.flush()

        order = await svc.create_order(
            {
                "company_id": CLIENT_ID,
                "own_company_id": str(lead.own_company_id or ""),
                "currency": "PLN",
                "notes": f"Path 3 sales bridge test · lead {lead.id}",
                "requested_by": "b97c3ee4-d0e5-429f-ab1d-762fc518363b",
                "audit": {"source": "client_lead_service_order", "lead_id": str(lead.id)},
            },
            [
                {"service_id": str(handoff.id), "qty": Decimal("1")},
                {"service_id": str(inline.id), "qty": Decimal("1")},
            ],
        )
        normalized["service_order_id"] = str(order.id)
        lead.normalized = normalized
        await db.commit()

        order = await svc.get_order(order.id)
        out = ServiceOrderOut.model_validate(order, from_attributes=True)
        modes = [i.execution_mode for i in out.items]
        step(
            "3. Service order from sales",
            {
                "order_id": out.id,
                "company_id": out.company_id,
                "beneficiary_kind": out.beneficiary_kind,
                "items": len(out.items),
                "execution_modes": modes,
            },
        )
        ok = (
            out.company_id == CLIENT_ID
            and out.beneficiary_kind == "client"
            and len(out.items) == 2
            and "handoff" in modes
            and "inline" in modes
        )
        results.append(("3_sales_order", "PASS" if ok else "FAIL"))

    step("SUMMARY", dict(results))
    if any(v == "FAIL" for _, v in results):
        print("\nPATH 3: FAIL", file=sys.stderr)
        return 1
    print("\nPATH 3: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
