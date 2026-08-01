#!/usr/bin/env python3
"""Cutover: snapshot tenant lead email preset onto OwnCompany (ADR-033 slice A).

For each tenant:
  - Build lead_lifecycle_email_v1 from tenant lead_rodo_v1 + lead_communication_v1
  - Write into OwnCompany.extra.lead_lifecycle_email_v1 when missing (unless --force)
  - Optionally also seed client companies (legacy P4 behaviour) via --also-client-companies
  - Mark tenant.settings.lead_lifecycle_email_own_company_cutover_v1.completed_at

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

from backend.app.db.session import async_session_maker as AsyncSessionLocal
from backend.app.models.company import Company
from backend.app.models.company_module_settings import CompanyModuleSettings
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.app.schemas.company_module_settings_json import normalize_company_module_settings_json
from backend.app.services.lead_lifecycle_email_policy import (
    cutover_completed,
    mark_cutover_completed,
    mark_own_company_cutover_completed,
    own_company_cutover_completed,
    set_own_company_lifecycle_policy,
    tenant_preset_to_company_policy,
)


async def _cutover_own_companies(
    db,
    tenant: Tenant,
    *,
    apply: bool,
    force: bool,
) -> dict[str, Any]:
    tid = str(tenant.id)
    settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    already = own_company_cutover_completed(settings)
    preset = tenant_preset_to_company_policy(settings)

    owns = (
        await db.execute(select(OwnCompany).where(OwnCompany.tenant_id == tid))
    ).scalars().all()

    updated = 0
    skipped = 0
    for own in owns:
        extra = dict(own.extra or {}) if isinstance(own.extra, dict) else {}
        existing = dict(extra.get("lead_lifecycle_email_v1") or {})
        if existing and not force:
            skipped += 1
            continue
        if not apply:
            updated += 1
            continue
        set_own_company_lifecycle_policy(own, preset)
        flag_modified(own, "extra")
        updated += 1

    if apply and (force or not already):
        now = datetime.now(timezone.utc).isoformat()
        tenant.settings = mark_own_company_cutover_completed(settings, at_iso=now)
        flag_modified(tenant, "settings")

    return {
        "own_companies": len(owns),
        "would_update" if not apply else "updated": updated,
        "skipped_existing": skipped,
        "already_own_cutover": already,
    }


async def _cutover_client_companies(
    db,
    tenant: Tenant,
    *,
    apply: bool,
    force: bool,
) -> dict[str, Any]:
    """Legacy P4: snapshot onto every client company as overlay seed."""
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
        # Re-read settings in case own cutover already mutated tenant.settings
        settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
        tenant.settings = mark_cutover_completed(settings, at_iso=now)
        flag_modified(tenant, "settings")

    return {
        "client_companies": len(companies),
        "would_update" if not apply else "updated": updated,
        "skipped_existing": skipped,
        "already_client_cutover": already,
    }


async def _cutover_tenant(
    db,
    tenant: Tenant,
    *,
    apply: bool,
    force: bool,
    also_client_companies: bool,
) -> dict[str, Any]:
    tid = str(tenant.id)
    settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    preset = tenant_preset_to_company_policy(settings)
    own_stats = await _cutover_own_companies(db, tenant, apply=apply, force=force)
    client_stats: dict[str, Any] = {}
    if also_client_companies:
        client_stats = await _cutover_client_companies(db, tenant, apply=apply, force=force)
    return {
        "tenant_id": tid,
        "preset_rodo_mode": preset.get("rodo_send_mode"),
        "preset_ops_enabled": preset.get("ops_enabled"),
        "own": own_stats,
        "client": client_stats or None,
    }


async def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist changes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run (default)")
    parser.add_argument("--tenant-id", type=str, default=None, help="Limit to one tenant")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite own companies (and client rows if requested) that already have a policy block",
    )
    parser.add_argument(
        "--also-client-companies",
        action="store_true",
        help="Also seed client company_module_settings overlays (legacy P4)",
    )
    args = parser.parse_args(argv)
    apply = bool(args.apply) and not bool(args.dry_run)

    async with AsyncSessionLocal() as db:
        q = select(Tenant)
        if args.tenant_id:
            q = q.where(Tenant.id == str(args.tenant_id).strip())
        tenants = (await db.execute(q)).scalars().all()
        results = []
        for tenant in tenants:
            results.append(
                await _cutover_tenant(
                    db,
                    tenant,
                    apply=apply,
                    force=args.force,
                    also_client_companies=bool(args.also_client_companies),
                )
            )
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
