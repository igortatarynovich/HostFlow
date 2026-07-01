#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services.operating_company_slots import (
    extract_extra_operating_company_slots,
    resolve_effective_company_limit,
)


LEGACY_SLOT_KEYS = (
    "additional_operating_company_slots",
    "operating_company_addon_slots",
)
CANONICAL_SLOT_KEY = "extra_operating_company_slots"


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _to_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _extract_raw_slot_values(subscription_payload: dict[str, Any]) -> dict[str, int]:
    keys = (CANONICAL_SLOT_KEY, *LEGACY_SLOT_KEYS)
    return {key: _to_int(subscription_payload.get(key)) for key in keys}


def _is_operating_company(company: Company) -> bool:
    extra = _as_dict(company.extra)
    role = str(extra.get("company_role") or "").strip().lower()
    return role == "operating"


def _tenant_billing_subscription(tenant: Tenant) -> dict[str, Any]:
    settings_payload = _as_dict(getattr(tenant, "settings", None))
    billing_payload = _as_dict(settings_payload.get("billing"))
    return _as_dict(billing_payload.get("subscription"))


def _set_tenant_billing_subscription(tenant: Tenant, subscription_payload: dict[str, Any]) -> None:
    settings_payload = _as_dict(getattr(tenant, "settings", None))
    billing_payload = _as_dict(settings_payload.get("billing"))
    billing_payload["subscription"] = subscription_payload
    settings_payload["billing"] = billing_payload
    tenant.settings = settings_payload
    tenant.updated_at = datetime.now(UTC)


@dataclass
class TenantAuditRow:
    tenant_id: str
    tenant_slug: str
    license_plan: str
    included_limit: int
    used_operating_companies: int
    canonical_extra_slots: int
    legacy_keys_present: list[str]
    raw_slot_values: dict[str, int]
    effective_limit: int
    overflow: bool
    suggested_extra_for_no_data_loss: int


async def _build_audit_rows() -> tuple[list[TenantAuditRow], dict[str, Any]]:
    async with async_session_maker() as db:
        tenants = (await db.execute(select(Tenant).order_by(Tenant.created_at.asc()))).scalars().all()
        licenses = (await db.execute(select(TenantLicense))).scalars().all()
        companies = (await db.execute(select(Company))).scalars().all()

    license_by_tenant = {str(row.tenant_id): row for row in licenses}
    operating_count_by_tenant: dict[str, int] = {}
    for company in companies:
        tenant_id = str(company.tenant_id)
        if not _is_operating_company(company):
            continue
        operating_count_by_tenant[tenant_id] = operating_count_by_tenant.get(tenant_id, 0) + 1

    rows: list[TenantAuditRow] = []
    overflow_tenants = 0
    legacy_key_tenants = 0
    no_license_tenants = 0
    for tenant in tenants:
        tenant_id = str(tenant.id)
        tenant_slug = str(getattr(tenant, "slug", "") or "")
        license_row = license_by_tenant.get(tenant_id)
        included_limit = int(getattr(license_row, "max_companies", 0) or 0)
        license_plan = str(getattr(license_row, "plan", "") or "")
        if license_row is None:
            no_license_tenants += 1

        used = int(operating_count_by_tenant.get(tenant_id, 0))
        subscription_payload = _tenant_billing_subscription(tenant)
        canonical_extra = extract_extra_operating_company_slots(subscription_payload)
        raw_values = _extract_raw_slot_values(subscription_payload)
        legacy_keys_present = [key for key in LEGACY_SLOT_KEYS if key in subscription_payload]
        if legacy_keys_present:
            legacy_key_tenants += 1

        effective_limit = resolve_effective_company_limit(included_limit, canonical_extra)
        overflow = effective_limit > 0 and used > effective_limit
        if overflow:
            overflow_tenants += 1
        suggested_extra = max(0, used - included_limit) if included_limit > 0 else 0
        rows.append(
            TenantAuditRow(
                tenant_id=tenant_id,
                tenant_slug=tenant_slug,
                license_plan=license_plan or "-",
                included_limit=included_limit,
                used_operating_companies=used,
                canonical_extra_slots=canonical_extra,
                legacy_keys_present=legacy_keys_present,
                raw_slot_values=raw_values,
                effective_limit=effective_limit,
                overflow=overflow,
                suggested_extra_for_no_data_loss=suggested_extra,
            )
        )

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "tenant_count": len(tenants),
        "overflow_tenants": overflow_tenants,
        "legacy_key_tenants": legacy_key_tenants,
        "tenants_without_license": no_license_tenants,
    }
    return rows, summary


def _markdown_report(rows: list[TenantAuditRow], summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# A6-S6 Operating Company Slots Dry-Run Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{summary['generated_at_utc']}`")
    lines.append(f"- Tenants audited: `{summary['tenant_count']}`")
    lines.append(f"- Overflow tenants (`used > effective_limit`): `{summary['overflow_tenants']}`")
    lines.append(f"- Tenants with legacy slot keys: `{summary['legacy_key_tenants']}`")
    lines.append(f"- Tenants without `tenant_licenses` row: `{summary['tenants_without_license']}`")
    lines.append("")
    lines.append("## Per-tenant table")
    lines.append("")
    lines.append(
        "| tenant_slug | plan | included | extra(canonical) | effective | used_operating | overflow | suggested_extra_no_data_loss | legacy_keys_present | raw_slot_values |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---|---:|---|---|")
    alias_by_tenant_id = {row.tenant_id: f"tenant-{index:02d}" for index, row in enumerate(rows, start=1)}
    for row in rows:
        effective = "∞" if row.effective_limit == 0 else str(row.effective_limit)
        legacy = ", ".join(row.legacy_keys_present) if row.legacy_keys_present else "-"
        raw_values = json.dumps(row.raw_slot_values, ensure_ascii=True, separators=(",", ":"))
        slug_or_alias = alias_by_tenant_id.get(row.tenant_id, row.tenant_slug or row.tenant_id)
        lines.append(
            f"| `{slug_or_alias}` | `{row.license_plan}` | {row.included_limit} | {row.canonical_extra_slots} | {effective} | {row.used_operating_companies} | {'YES' if row.overflow else 'NO'} | {row.suggested_extra_for_no_data_loss} | `{legacy}` | `{raw_values}` |"
        )
    lines.append("")
    lines.append("## Recommended transition actions")
    lines.append("")
    lines.append("1. Normalize all tenant subscription payloads to canonical key `extra_operating_company_slots` and remove legacy aliases.")
    lines.append("2. For tenants in overflow, do not delete companies; keep data as-is and block only new operating company creation until limits match.")
    lines.append("3. If Product approves grace-policy, set temporary `extra_operating_company_slots = suggested_extra_no_data_loss` for overflow tenants.")
    lines.append("4. Attach this report to release evidence before switching A6-S6 to DONE.")
    lines.append("")
    return "\n".join(lines)


async def _apply_normalization(rows: list[TenantAuditRow]) -> int:
    updated = 0
    by_tenant = {row.tenant_id: row for row in rows}
    async with async_session_maker() as db:
        tenants = (await db.execute(select(Tenant))).scalars().all()
        for tenant in tenants:
            row = by_tenant.get(str(tenant.id))
            if row is None:
                continue
            subscription_payload = _tenant_billing_subscription(tenant)
            if not subscription_payload:
                continue
            next_payload = dict(subscription_payload)
            next_payload[CANONICAL_SLOT_KEY] = row.canonical_extra_slots
            changed = str(subscription_payload.get(CANONICAL_SLOT_KEY, "")) != str(row.canonical_extra_slots)
            for legacy_key in LEGACY_SLOT_KEYS:
                if legacy_key in next_payload:
                    del next_payload[legacy_key]
                    changed = True
            if not changed:
                continue
            _set_tenant_billing_subscription(tenant, next_payload)
            updated += 1
        if updated:
            await db.commit()
    return updated


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="A6-S6 dry-run audit for operating company slots migration/transition.",
    )
    parser.add_argument(
        "--report",
        default="docs/manual-checklist/a6-s6-operating-slots-dry-run.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--json",
        default="",
        help="Optional JSON report output path.",
    )
    parser.add_argument(
        "--apply-normalize-keys",
        action="store_true",
        help="Apply canonical key normalization in tenant settings (non-destructive, no slot amount changes).",
    )
    args = parser.parse_args()

    rows, summary = await _build_audit_rows()
    report_md = _markdown_report(rows, summary)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")
    print(f"[a6-s6] markdown report written: {report_path}")

    if args.json:
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_payload = {
            "summary": summary,
            "rows": [
                {
                    "tenant_id": row.tenant_id,
                    "tenant_slug": row.tenant_slug,
                    "license_plan": row.license_plan,
                    "included_limit": row.included_limit,
                    "used_operating_companies": row.used_operating_companies,
                    "canonical_extra_slots": row.canonical_extra_slots,
                    "legacy_keys_present": row.legacy_keys_present,
                    "raw_slot_values": row.raw_slot_values,
                    "effective_limit": row.effective_limit,
                    "overflow": row.overflow,
                    "suggested_extra_for_no_data_loss": row.suggested_extra_for_no_data_loss,
                }
                for row in rows
            ],
        }
        json_path.write_text(json.dumps(json_payload, ensure_ascii=True, indent=2), encoding="utf-8")
        print(f"[a6-s6] json report written: {json_path}")

    if args.apply_normalize_keys:
        updated = await _apply_normalization(rows)
        print(f"[a6-s6] normalized tenant subscription payloads: {updated}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
