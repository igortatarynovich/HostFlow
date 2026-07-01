#!/usr/bin/env python3
"""
Выдать тенанту план Business без Stripe (внутренний comp / оператор).

В коде план называется ``pro`` (см. PLAN_LICENSE_LIMITS в billing.py); в UI — Business.
Обновляет:
  - tenants.settings.billing.subscription (mock, active, plan_code=pro)
  - tenant_licenses (лимиты как у Business)

Запуск из корня репозитория (как и другие backend-скрипты):

  cd /opt/HostFlow
  DATABASE_URL=postgresql+asyncpg://... python3 scripts/grant_tenant_business_internal.py

  # только Focus Personnel по умолчанию:
  python3 scripts/grant_tenant_business_internal.py

  # другой tenant:
  python3 scripts/grant_tenant_business_internal.py --tenant-id <uuid>

  # проверка без записи:
  python3 scripts/grant_tenant_business_internal.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from backend.app.api.v1.settings.billing import (  # noqa: E402
    _apply_license_limits,
    _history_entry,
    _now_utc,
    _store_subscription,
    _subscription_payload,
)
from backend.app.constants.hostflow_canonical_tenants import FOCUS_PERSONNEL_TENANT_ID  # noqa: E402
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.tenant import Tenant  # noqa: E402


async def run(*, tenant_id: str, dry_run: bool) -> None:
    async with async_session_maker() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            print(f"ERROR: tenant not found: {tenant_id}", file=sys.stderr)
            sys.exit(1)
        print(f"Tenant: {tenant.name} ({tenant.id})")
        current = _subscription_payload(tenant)
        now = _now_utc()
        period_days = 30
        merged = {
            **current,
            "provider": "mock",
            "status": "active",
            "plan_code": "pro",
            "billing_interval": "month",
            "billing_contact_email": current.get("billing_contact_email"),
            "cancel_at_period_end": False,
            "canceled_at": None,
            "pending_update": False,
            "pending_plan_code": None,
            "pending_invoice_id": None,
            "pending_invoice_url": None,
            "checkout_session_id": None,
            "subscription_id": None,
            "customer_id": None,
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=period_days)).isoformat(),
            "activated_at": str(current.get("activated_at") or "").strip() or now.isoformat(),
            "updated_at": now.isoformat(),
        }
        hist = _history_entry(
            event_type="subscription.plan_changed",
            status="success",
            title="Internal plan grant (Business)",
            description="Operator comp: Business (pro) without Stripe charge.",
            source="app",
            plan_code="pro",
            dedupe_key=f"internal:grant-business:{tenant_id}:{now.isoformat()}",
        )
        if dry_run:
            print("DRY RUN — would set subscription:", {k: merged[k] for k in ("provider", "status", "plan_code") if k in merged})
            print("DRY RUN — would apply tenant_licenses limits for plan_code=pro")
            return
        await _store_subscription(db, tenant, merged, history_entry=hist)
        await _apply_license_limits(db, tenant_id, "pro")
        print("OK: Business (pro) applied; billing UI should show Business on next load.")


def main() -> None:
    p = argparse.ArgumentParser(description="Grant internal Business (pro) plan to a tenant.")
    p.add_argument(
        "--tenant-id",
        default=FOCUS_PERSONNEL_TENANT_ID,
        help=f"Target tenant UUID (default: Focus Personnel = {FOCUS_PERSONNEL_TENANT_ID})",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(run(tenant_id=str(args.tenant_id).strip(), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
