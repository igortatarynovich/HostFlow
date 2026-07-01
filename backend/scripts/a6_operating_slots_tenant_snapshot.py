#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services.operating_company_slots import get_operating_company_slots


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _company_role(company: Company) -> str:
    extra = _as_dict(getattr(company, "extra", None))
    return str(extra.get("company_role") or "").strip().lower() or "client"


def _resolve_docs_root() -> Path:
    candidates = [
        Path("/app/docs"),
        REPO_ROOT.parent / "docs",
        Path.cwd() / "docs",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


async def _load_tenant(db, *, tenant_slug: str | None, tenant_id: str | None) -> Tenant | None:
    if tenant_id:
        return await db.get(Tenant, tenant_id)
    if tenant_slug:
        return (
            await db.execute(select(Tenant).where(Tenant.slug == tenant_slug).limit(1))
        ).scalar_one_or_none()
    return None


async def build_snapshot(*, tenant_slug: str | None, tenant_id: str | None) -> dict[str, Any]:
    async with async_session_maker() as db:
        tenant = await _load_tenant(db, tenant_slug=tenant_slug, tenant_id=tenant_id)
        if tenant is None:
            raise ValueError("Tenant not found")

        resolved_tenant_id = str(tenant.id)
        license_row = (
            await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == resolved_tenant_id).limit(1))
        ).scalar_one_or_none()
        companies = (
            await db.execute(
                select(Company)
                .where(Company.tenant_id == resolved_tenant_id)
                .order_by(Company.created_at.asc())
            )
        ).scalars().all()
        slots = await get_operating_company_slots(
            db,
            resolved_tenant_id,
            preloaded_tenant=tenant,
            preloaded_license=license_row,
        )

        settings_payload = _as_dict(getattr(tenant, "settings", None))
        billing_payload = _as_dict(settings_payload.get("billing"))
        subscription_payload = _as_dict(billing_payload.get("subscription"))

        companies_payload = []
        for company in companies:
            role = _company_role(company)
            companies_payload.append(
                {
                    "id": str(company.id),
                    "name": str(getattr(company, "name", "") or ""),
                    "company_role": role,
                    "company_type": str(_as_dict(getattr(company, "extra", None)).get("company_type") or ""),
                    "owner_user_id": str(getattr(company, "owner_user_id", "") or ""),
                    "manager_user_id": str(getattr(company, "manager_user_id", "") or ""),
                    "created_at": getattr(company, "created_at").isoformat() if getattr(company, "created_at", None) else None,
                }
            )

        return {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "tenant": {
                "id": resolved_tenant_id,
                "slug": str(getattr(tenant, "slug", "") or ""),
                "name": str(getattr(tenant, "name", "") or ""),
                "status": str(getattr(getattr(tenant, "status", None), "value", getattr(tenant, "status", "")) or ""),
                "type": str(getattr(getattr(tenant, "type", None), "value", getattr(tenant, "type", "")) or ""),
            },
            "license": {
                "plan": str(getattr(license_row, "plan", "") or ""),
                "max_companies": int(getattr(license_row, "max_companies", 0) or 0),
            }
            if license_row
            else None,
            "slots": {
                "included_limit": int(slots.included_limit),
                "extra_slots": int(slots.extra_slots),
                "effective_limit": int(slots.effective_limit),
                "used": int(slots.used),
                "available": int(slots.available),
                "unlimited": bool(slots.unlimited),
            },
            "subscription": {
                "provider": str(subscription_payload.get("provider") or ""),
                "status": str(subscription_payload.get("status") or ""),
                "plan_code": str(subscription_payload.get("plan_code") or ""),
                "subscription_id": str(subscription_payload.get("subscription_id") or ""),
                "customer_id": str(subscription_payload.get("customer_id") or ""),
                "extra_operating_company_slots": int(subscription_payload.get("extra_operating_company_slots") or 0),
                "pending_update": bool(subscription_payload.get("pending_update")),
                "pending_plan_code": str(subscription_payload.get("pending_plan_code") or ""),
                "current_period_end": str(subscription_payload.get("current_period_end") or ""),
                "updated_at": str(subscription_payload.get("updated_at") or ""),
            },
            "companies": companies_payload,
            "operating_companies": [item for item in companies_payload if item.get("company_role") == "operating"],
        }


def to_markdown(snapshot: dict[str, Any]) -> str:
    tenant = snapshot["tenant"]
    slots = snapshot["slots"]
    subscription = snapshot["subscription"]
    lines: list[str] = []
    lines.append("# A6-S7 Tenant Slots Snapshot")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{snapshot['generated_at_utc']}`")
    lines.append(f"- Tenant: `{tenant['slug']}` (`{tenant['id']}`)")
    lines.append(f"- Tenant status/type: `{tenant['status']}` / `{tenant['type']}`")
    lines.append("")
    lines.append("## Slots")
    lines.append("")
    lines.append(
        f"- Included: `{slots['included_limit']}`, Extra: `{slots['extra_slots']}`, Effective: `{slots['effective_limit']}`, Used: `{slots['used']}`, Available: `{slots['available']}`"
    )
    lines.append("")
    lines.append("## Subscription")
    lines.append("")
    lines.append(
        f"- Provider/status/plan: `{subscription['provider']}` / `{subscription['status']}` / `{subscription['plan_code']}`"
    )
    lines.append(
        f"- Stripe ids: subscription=`{subscription['subscription_id']}`, customer=`{subscription['customer_id']}`"
    )
    lines.append(f"- extra_operating_company_slots: `{subscription['extra_operating_company_slots']}`")
    lines.append("")
    lines.append("## Operating Companies")
    lines.append("")
    lines.append("| Name | Role | Type | Owner | Manager | Created at |")
    lines.append("|---|---|---|---|---|---|")
    for company in snapshot["operating_companies"]:
        lines.append(
            f"| {company['name']} | `{company['company_role']}` | `{company['company_type']}` | `{company['owner_user_id']}` | `{company['manager_user_id']}` | `{company['created_at'] or ''}` |"
        )
    if not snapshot["operating_companies"]:
        lines.append("| _none_ |  |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Capture A6-S7 tenant slot snapshot for manual evidence.")
    parser.add_argument("--tenant-slug", default="", help="Tenant slug.")
    parser.add_argument("--tenant-id", default="", help="Tenant id.")
    parser.add_argument("--label", default="", help="Optional label (before/after/downgrade).")
    parser.add_argument("--report", default="", help="Markdown report output path.")
    parser.add_argument("--json", default="", help="JSON output path.")
    args = parser.parse_args()

    tenant_slug = str(args.tenant_slug or "").strip() or None
    tenant_id = str(args.tenant_id or "").strip() or None
    if not tenant_slug and not tenant_id:
        print("ERROR: provide --tenant-slug or --tenant-id")
        return 2

    docs_root = _resolve_docs_root()
    today = date.today().isoformat()
    tenant_alias = tenant_slug or (tenant_id or "tenant")
    safe_alias = tenant_alias.replace("/", "-").replace(" ", "-")
    label = str(args.label or "").strip()
    suffix = f"-{label}" if label else ""

    report_path = Path(args.report) if args.report else docs_root / "manual-checklist" / f"a6-s7-slots-snapshot-{today}-{safe_alias}{suffix}.md"
    json_path = Path(args.json) if args.json else docs_root / "manual-checklist" / f"a6-s7-slots-snapshot-{today}-{safe_alias}{suffix}.json"

    try:
        snapshot = await build_snapshot(tenant_slug=tenant_slug, tenant_id=tenant_id)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    report_md = to_markdown(snapshot)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(snapshot, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"[a6-s7] markdown snapshot written: {report_path}")
    print(f"[a6-s7] json snapshot written: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
