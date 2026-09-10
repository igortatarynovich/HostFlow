#!/usr/bin/env python3
"""
Ensure the Meta App Review demo profile can open Meta Leads + start Facebook OAuth (ads_read).

Default target: demo@hostflow.dev on EuroDrive Recruiting.

  cd /opt/HostFlow
  python3 scripts/ensure_meta_app_review_demo.py --dry-run
  python3 scripts/ensure_meta_app_review_demo.py --password '…'
  python3 scripts/ensure_meta_app_review_demo.py --password '…' --fix-legacy-mapping

Does not create Facebook Test Users (Meta Developers console).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.security import hash_password  # noqa: E402
from backend.app.db.session import async_session_maker  # noqa: E402

DEFAULT_EMAIL = "demo@hostflow.dev"
DEFAULT_TENANT_ID = "6f83284f-3b77-4ef4-b8eb-5acdedf26d60"

LEGACY_MAPPING_FIX = [
    {"source": "full_name", "target": "full_name", "format": "string", "overwrite": True},
    {"source": "email", "target": "email", "format": "email", "overwrite": True},
    {"source": "phone_number", "target": "phone", "format": "phone", "overwrite": True},
]


async def run(*, email: str, tenant_id: str, password: str | None, fix_mapping: bool, dry_run: bool) -> int:
    async with async_session_maker() as db:
        await db.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": tenant_id})

        user = (
            await db.execute(
                text(
                    """
                    SELECT u.id::text, u.email, u.role,
                           um.role AS membership_role, t.name AS tenant_name, t.status AS tenant_status
                    FROM users u
                    JOIN user_memberships um ON um.user_id = u.id
                    JOIN tenants t ON t.id = um.tenant_id
                    WHERE lower(u.email) = lower(:email) AND um.tenant_id = :tenant
                    """
                ),
                {"email": email, "tenant": tenant_id},
            )
        ).mappings().first()
        if not user:
            print(f"ERROR: user {email} not found on tenant {tenant_id}", file=sys.stderr)
            return 1

        lic = (
            await db.execute(
                text("SELECT plan FROM tenant_licenses WHERE tenant_id = :t"),
                {"t": tenant_id},
            )
        ).mappings().first()
        plan = (lic or {}).get("plan") if lic else None

        settings_row = (
            await db.execute(
                text(
                    """
                    SELECT field_mapping,
                           webhook_verify_token IS NOT NULL
                             AND length(trim(webhook_verify_token)) > 0 AS has_verify
                    FROM meta_lead_settings WHERE tenant_id = :t
                    """
                ),
                {"t": tenant_id},
            )
        ).mappings().first()

        bad_targets = (
            await db.execute(
                text(
                    """
                    SELECT count(*)::int AS n
                    FROM leads
                    WHERE tenant_id = :t
                      AND lead_target_type NOT IN
                          ('candidate','client_lead','service_order_lead','partner_lead')
                    """
                ),
                {"t": tenant_id},
            )
        ).scalar_one()

        print("Demo profile")
        print(f"  user:     {user['email']} ({user['id']})")
        print(f"  role:     users.role={user['role']} membership={user['membership_role']}")
        print(f"  tenant:   {user['tenant_name']} ({tenant_id}) status={user['tenant_status']}")
        print(f"  plan:     {plan}")
        print(f"  verify:   {bool(settings_row and settings_row['has_verify'])}")
        print(f"  bad LTT:  {bad_targets}")

        mapping = (settings_row or {}).get("field_mapping") if settings_row else None
        legacy_from_to = False
        if isinstance(mapping, list) and mapping:
            legacy_from_to = any(
                isinstance(r, dict) and ("from" in r or "to" in r) and "source" not in r for r in mapping
            )
        print(f"  mapping:  legacy_from_to={legacy_from_to}")

        ok_role = str(user["membership_role"] or user["role"] or "").lower() in {
            "administrator",
            "superadmin",
            "admin",
        }
        if not ok_role:
            print("WARN: user is not administrator — Connect with Meta will be hidden")

        if dry_run:
            print("DRY RUN — no writes")
            return 0 if ok_role else 2

        if password:
            await db.execute(
                text("UPDATE users SET password_hash = :h, updated_at = now() WHERE id = :id"),
                {"h": hash_password(password), "id": user["id"]},
            )
            print("OK: password updated")

        if fix_mapping and (legacy_from_to or mapping is None):
            await db.execute(
                text(
                    """
                    UPDATE meta_lead_settings
                    SET field_mapping = CAST(:m AS jsonb), updated_at = now()
                    WHERE tenant_id = :t
                    """
                ),
                {"m": json.dumps(LEGACY_MAPPING_FIX), "t": tenant_id},
            )
            print("OK: field_mapping normalized")

        if bad_targets:
            await db.execute(
                text(
                    """
                    UPDATE leads
                    SET lead_target_type = 'candidate'
                    WHERE tenant_id = :t
                      AND lead_target_type NOT IN
                          ('candidate','client_lead','service_order_lead','partner_lead')
                    """
                ),
                {"t": tenant_id},
            )
            print(f"OK: normalized {bad_targets} lead_target_type row(s)")

        await db.commit()
        print("Done. Verify: login → Settings → Integrations → Meta → Connect with Meta.")
        return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Ensure Meta App Review demo profile")
    p.add_argument("--email", default=DEFAULT_EMAIL)
    p.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    p.add_argument("--password", default=None, help="Reset HostFlow login password")
    p.add_argument(
        "--fix-legacy-mapping",
        action="store_true",
        help="Rewrite legacy {from,to} Meta field_mapping to source/target",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    raise SystemExit(
        asyncio.run(
            run(
                email=args.email.strip(),
                tenant_id=args.tenant_id.strip(),
                password=args.password,
                fix_mapping=bool(args.fix_legacy_mapping),
                dry_run=bool(args.dry_run),
            )
        )
    )


if __name__ == "__main__":
    main()
