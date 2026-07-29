#!/usr/bin/env python3
"""P4 cutover: snapshot tenant lead email preset onto every company (ADR-033).

For each tenant:
  - Build lead_lifecycle_email_v1 from tenant lead_rodo_v1 + lead_communication_v1
  - Upsert into company_module_settings (module_key=recruitment) for every company
    that does not already have a non-empty lead_lifecycle_email_v1 block
  - Mark tenant.settings.lead_lifecycle_email_cutover_v1.completed_at

Usage (from repo root, with DB env loaded)::

    PYTHONPATH=backend python backend/scripts/cutover_lead_lifecycle_email_company_policy.py --dry-run
    PYTHONPATH=backend python backend/scripts/cutover_lead_lifecycle_email_company_policy.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from backend.app.db.session import async_session_maker
from backend.app.models.company import Company
from backend.app.models.company_module_settings import CompanyModuleSettings
from backend.app.models.tenant import Tenant
from backend.app.schemas.company_module_settings_json import normalize_company_module_settings_json
from backend.app.services.lead_lifecycle_email_policy import (
    CUTOVER_SETTINGS_KEY,
    cutover_completed,
    mark_cutover_completed,
    tenant_preset_to_company_policy,
)


async def _cutover_tenant(
    db,
    tenant: Tenant,
    *,
    apply: bool,
    force: bool,
) -> dict[str, Any]:
    tid = str(tenant.id)
    settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    already = cutover_completed(settings)
    preset = tenant_preset_to_company_policy(settings)

    companies = (
        await db.execute(select(Company).where(Company.tenant_id == tid))
    ).scalars().all()

    updated = 0
    skipped = 0
    for company in companies:
        cid = str(company.id)
        row = (
            await db.execute(
                select(CompanyModuleSettings).where(
                    CompanyModuleSettings.tenant_id == tid,
                    CompanyModuleSettings.company_id == cid,
                    CompanyModuleSettings.module_key == "recruitment",
                )
            )
        ).scalar_one_or_none()
        existing = {}
        if row is not None and isinstance(row.settings_json, dict):
            existing = dict(row.settings_json.get("lead_lifecycle_email_v1") or {})
        if existing and not force:
            skipped += 1
            continue
        merged = dict(row.settings_json or {}) if row is not None else {}
        merged["lead_lifecycle_email_v1"] = preset
        normalized = normalize_company_module_settings_json("recruitment", merged)
        if not apply:
            updated += 1
            continue
        if row is None:
            row = CompanyModuleSettings(
                id=str(uuid4()),
                tenant_id=tid,
                company_id=cid,
                module_key="recruitment",
                settings_json=normalized,
                is_enabled=True,
            )
            db.add(row)
        else:
            row.settings_json = normalized
            flag_modified(row, "settings_json")
        updated += 1

    if apply and (force or not already):
        now = datetime.now(timezone.utc).isoformat()
        tenant.settings = mark_cutover_completed(settings, at_iso=now)
        flag_modified(tenant, "settings")

    return {
        "tenant_id": tid,
        "companies": len(companies),
        "would_update" if not apply else "updated": updated,
        "skipped_existing": skipped,
        "already_cutover": already,
        "preset_rodo_mode": preset.get("rodo_send_mode"),
        "preset_ops_enabled": preset.get("ops_enabled"),
    }


async def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist changes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run (default)")
    parser.add_argument("--tenant-id", type=str, default=None, help="Limit to one tenant")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite companies that already have lead_lifecycle_email_v1",
    )
    args = parser.parse_args(argv)
    apply = bool(args.apply) and not bool(args.dry_run)

    async with async_session_maker() as db:
        q = select(Tenant)
        if args.tenant_id:
            q = q.where(Tenant.id == str(args.tenant_id).strip())
        tenants = (await db.execute(q)).scalars().all()
        results = []
        for tenant in tenants:
            results.append(await _cutover_tenant(db, tenant, apply=apply, force=args.force))
        if apply:
            await db.commit()
        for row in results:
            print(row)

    print(f"done mode={'apply' if apply else 'dry-run'} tenants={len(results)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
