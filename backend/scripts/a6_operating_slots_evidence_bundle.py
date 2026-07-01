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


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _resolve_docs_root() -> Path:
    candidates = [
        Path("/opt/HostFlow/docs"),
        REPO_ROOT.parent / "docs",
        Path.cwd() / "docs",
        Path("/app/docs"),
    ]
    marker = Path("manual-checklist") / "a6-s7-manual-evidence-checklist.md"
    for candidate in candidates:
        if (candidate / marker).exists():
            return candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _company_role(company: Company) -> str:
    extra = _as_dict(getattr(company, "extra", None))
    return str(extra.get("company_role") or "").strip().lower() or "client"


async def _find_tenant(db, *, tenant_slug: str | None, tenant_id: str | None) -> Tenant | None:
    if tenant_id:
        return await db.get(Tenant, tenant_id)
    if tenant_slug:
        return (
            await db.execute(select(Tenant).where(Tenant.slug == tenant_slug).limit(1))
        ).scalar_one_or_none()
    return None


def _history_item_payload(item: Any) -> dict[str, Any]:
    row = _as_dict(item)
    return {
        "occurred_at": str(row.get("occurred_at") or ""),
        "event_type": str(row.get("event_type") or ""),
        "status": str(row.get("status") or ""),
        "title": str(row.get("title") or ""),
        "description": str(row.get("description") or ""),
        "plan_code": str(row.get("plan_code") or ""),
        "invoice_id": str(row.get("invoice_id") or ""),
    }


async def build_bundle(*, tenant_slug: str | None, tenant_id: str | None, history_limit: int) -> dict[str, Any]:
    async with async_session_maker() as db:
        tenant = await _find_tenant(db, tenant_slug=tenant_slug, tenant_id=tenant_id)
        if tenant is None:
            raise ValueError("Tenant not found")

        resolved_tenant_id = str(tenant.id)
        license_row = (
            await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == resolved_tenant_id).limit(1))
        ).scalar_one_or_none()
        companies = (
            await db.execute(select(Company).where(Company.tenant_id == resolved_tenant_id).order_by(Company.created_at.asc()))
        ).scalars().all()

        settings_payload = _as_dict(getattr(tenant, "settings", None))
        billing_payload = _as_dict(settings_payload.get("billing"))
        subscription_payload = _as_dict(billing_payload.get("subscription"))
        history_payload = _as_list(billing_payload.get("history"))
        invoices_payload = _as_list(billing_payload.get("invoices"))

        slots = await get_operating_company_slots(
            db,
            resolved_tenant_id,
            preloaded_tenant=tenant,
            preloaded_license=license_row,
        )

        operating_companies = []
        for company in companies:
            role = _company_role(company)
            if role != "operating":
                continue
            extra = _as_dict(getattr(company, "extra", None))
            operating_companies.append(
                {
                    "id": str(company.id),
                    "name": str(getattr(company, "name", "") or ""),
                    "company_type": str(extra.get("company_type") or ""),
                    "owner_user_id": str(getattr(company, "owner_user_id", "") or ""),
                    "manager_user_id": str(getattr(company, "manager_user_id", "") or ""),
                    "created_at": getattr(company, "created_at").isoformat() if getattr(company, "created_at", None) else None,
                }
            )

        history_tail = [_history_item_payload(item) for item in history_payload][-history_limit:]
        invoices_tail = [_as_dict(item) for item in invoices_payload][-history_limit:]

        quality_gates = {
            "has_stripe_customer": bool(str(subscription_payload.get("customer_id") or "").strip()),
            "has_subscription_id": bool(str(subscription_payload.get("subscription_id") or "").strip()),
            "has_billing_history": len(history_payload) > 0,
            "has_invoice_records": len(invoices_payload) > 0,
            "operating_over_limit_state": slots.effective_limit > 0 and slots.used > slots.effective_limit,
        }

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
                "pending_plan_code": str(subscription_payload.get("pending_plan_code") or ""),
                "pending_update": bool(subscription_payload.get("pending_update")),
                "customer_id": str(subscription_payload.get("customer_id") or ""),
                "subscription_id": str(subscription_payload.get("subscription_id") or ""),
                "extra_operating_company_slots": int(subscription_payload.get("extra_operating_company_slots") or 0),
                "current_period_end": str(subscription_payload.get("current_period_end") or ""),
                "updated_at": str(subscription_payload.get("updated_at") or ""),
            },
            "operating_companies": operating_companies,
            "billing_history_tail": history_tail,
            "billing_invoices_tail": invoices_tail,
            "quality_gates": quality_gates,
        }


def to_markdown(bundle: dict[str, Any]) -> str:
    tenant = bundle["tenant"]
    slots = bundle["slots"]
    subscription = bundle["subscription"]
    gates = bundle["quality_gates"]

    lines: list[str] = []
    lines.append("# A6-S7 Tenant Evidence Bundle")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{bundle['generated_at_utc']}`")
    lines.append(f"- Tenant: `{tenant['slug']}` (`{tenant['id']}`)")
    lines.append("")
    lines.append("## Slots")
    lines.append("")
    lines.append(
        f"- Included `{slots['included_limit']}`, Extra `{slots['extra_slots']}`, Effective `{slots['effective_limit']}`, Used `{slots['used']}`, Available `{slots['available']}`"
    )
    lines.append("")
    lines.append("## Subscription")
    lines.append("")
    lines.append(f"- Provider/status/plan: `{subscription['provider']}` / `{subscription['status']}` / `{subscription['plan_code']}`")
    lines.append(f"- Stripe IDs: customer=`{subscription['customer_id']}`, subscription=`{subscription['subscription_id']}`")
    lines.append("")
    lines.append("## Quality Gates")
    lines.append("")
    for key, value in gates.items():
        lines.append(f"- `{key}`: `{'PASS' if value else 'MISSING/NO'}`")
    lines.append("")
    lines.append("## Operating Companies")
    lines.append("")
    lines.append("| Name | Type | Owner | Manager | Created |")
    lines.append("|---|---|---|---|---|")
    for item in bundle["operating_companies"]:
        lines.append(
            f"| {item['name']} | `{item['company_type']}` | `{item['owner_user_id']}` | `{item['manager_user_id']}` | `{item['created_at'] or ''}` |"
        )
    if not bundle["operating_companies"]:
        lines.append("| _none_ |  |  |  |  |")
    lines.append("")
    lines.append("## Billing History Tail")
    lines.append("")
    lines.append("| occurred_at | event_type | status | title | invoice_id |")
    lines.append("|---|---|---|---|---|")
    for row in bundle["billing_history_tail"]:
        lines.append(
            f"| `{row['occurred_at']}` | `{row['event_type']}` | `{row['status']}` | {row['title']} | `{row['invoice_id']}` |"
        )
    if not bundle["billing_history_tail"]:
        lines.append("| _none_ |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Collect A6-S7 evidence bundle for a real tenant.")
    parser.add_argument("--tenant-slug", default="", help="Tenant slug.")
    parser.add_argument("--tenant-id", default="", help="Tenant id.")
    parser.add_argument("--history-limit", type=int, default=15, help="Number of history/invoice entries in tail.")
    parser.add_argument("--label", default="", help="Optional label suffix (before/after).")
    parser.add_argument("--docs-root", default="", help="Override docs root path.")
    parser.add_argument("--report", default="", help="Markdown report path.")
    parser.add_argument("--json", default="", help="JSON path.")
    args = parser.parse_args()

    tenant_slug = str(args.tenant_slug or "").strip() or None
    tenant_id = str(args.tenant_id or "").strip() or None
    if not tenant_slug and not tenant_id:
        print("ERROR: provide --tenant-slug or --tenant-id")
        return 2

    docs_root = Path(str(args.docs_root).strip()) if str(args.docs_root).strip() else _resolve_docs_root()
    today = date.today().isoformat()
    tenant_alias = tenant_slug or (tenant_id or "tenant")
    safe_alias = tenant_alias.replace("/", "-").replace(" ", "-")
    label = str(args.label or "").strip()
    suffix = f"-{label}" if label else ""

    report_path = Path(args.report) if args.report else docs_root / "manual-checklist" / f"a6-s7-evidence-bundle-{today}-{safe_alias}{suffix}.md"
    json_path = Path(args.json) if args.json else docs_root / "manual-checklist" / f"a6-s7-evidence-bundle-{today}-{safe_alias}{suffix}.json"

    try:
        bundle = await build_bundle(
            tenant_slug=tenant_slug,
            tenant_id=tenant_id,
            history_limit=max(1, int(args.history_limit)),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    report_md = to_markdown(bundle)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"[a6-s7] markdown evidence written: {report_path}")
    print(f"[a6-s7] json evidence written: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
