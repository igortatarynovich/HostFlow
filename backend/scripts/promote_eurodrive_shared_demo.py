#!/usr/bin/env python3
"""Promote EuroDrive Recruiting into a shareable screenshot/demo tenant.

- Tenant status: trial → active
- License: trial → enterprise (Focus-like limits, far expiry)
- Demo admin: demo@hostflow.dev / Demo@HostFlow1 (same user id as before)
- Personal account: move igor.tatarynovich@gmail.com to a private workspace
- Scrub personal email from company contacts / Meta account_ref
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from backend.app.core.security import hash_password
from backend.app.models import Company, Tenant, User
from backend.app.models.tenant import TenantLicense, TenantStatus, TenantType, user_memberships
from backend.app.models.user import Role

EURODRIVE_TENANT_ID = "6f83284f-3b77-4ef4-b8eb-5acdedf26d60"
DEMO_ADMIN_ID = "ced40564-e7e8-4acb-b7a1-305edeefcb85"
DEMO_EMAIL = "demo@hostflow.dev"
DEMO_PASSWORD = "Demo@HostFlow1"
DEMO_FULL_NAME = "Adam Nowak"
PERSONAL_EMAIL = "igor.tatarynovich@gmail.com"
OWN_COMPANY_ID = "b2222222-2222-4222-8222-222222222201"


def _db_url() -> str:
    url = (
        os.getenv("ASYNC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow"
    )
    if url.startswith("postgresql+psycopg"):
        url = url.replace("postgresql+psycopg", "postgresql+asyncpg", 1)
    return url


async def main() -> None:
    engine = create_async_engine(_db_url(), future=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == EURODRIVE_TENANT_ID).limit(1))
        ).scalar_one()
        demo_user = (
            await db.execute(select(User).where(User.id == DEMO_ADMIN_ID).limit(1))
        ).scalar_one()

        # Preserve password for personal account before rebinding demo user.
        personal_password_hash = demo_user.password_hash
        personal_preferences = (
            demo_user.preferences if isinstance(demo_user.preferences, dict) else {}
        )

        # --- EuroDrive: active + enterprise license ---
        tenant.status = TenantStatus.active
        settings = dict(tenant.settings or {})
        settings["shared_demo"] = True
        settings["shared_demo_login"] = DEMO_EMAIL
        onboarding = dict(settings.get("onboarding") or {})
        onboarding["workspace_name"] = "EuroDrive Sp. z o.o."
        onboarding["screenshot_pack"] = "eurodrive_v1"
        settings["onboarding"] = onboarding
        # Drop self-service signup marker that reads as "trial workspace"
        signup = dict(settings.get("signup") or {})
        signup["source"] = "shared_demo"
        settings["signup"] = signup
        tenant.settings = settings
        tenant.description = "Shared HostFlow screenshot / sales demo tenant (EuroDrive)."

        # Mock subscription must be active — API defaults missing sub to status=trial.
        billing = dict(settings.get("billing") or {})
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        billing["subscription"] = {
            "provider": "mock",
            "status": "active",
            "plan_code": "enterprise",
            "billing_interval": "year",
            "activated_at": now_iso,
            "updated_at": now_iso,
            "trial_ends_at": None,
            "cancel_at_period_end": False,
        }
        settings["billing"] = billing
        tenant.settings = settings

        lic = (
            await db.execute(
                select(TenantLicense).where(TenantLicense.tenant_id == EURODRIVE_TENANT_ID).limit(1)
            )
        ).scalar_one()
        lic.plan = "enterprise"
        lic.max_recruiters = 25
        lic.max_supervisors = 10
        lic.max_client_managers = 5
        lic.max_viewers = 50
        lic.max_storage_gb = 1000
        lic.max_companies = 10
        lic.max_candidates_active = 50000
        lic.max_vacancies_active = 5000
        lic.max_documents = 500000
        lic.max_public_portal_links = 100
        lic.expires_at = date(2030, 12, 31)
        lic.auto_renew = True
        lic.notes = "shared-screenshot-demo"
        await db.execute(
            text(
                """
                UPDATE tenant_licenses
                SET max_fleet_managers = 7
                WHERE tenant_id = :tid
                """
            ),
            {"tid": EURODRIVE_TENANT_ID},
        )

        # --- Rebind EuroDrive admin to demo credentials ---
        existing_demo = (
            await db.execute(select(User).where(User.email == DEMO_EMAIL).limit(1))
        ).scalar_one_or_none()
        if existing_demo and existing_demo.id != DEMO_ADMIN_ID:
            raise RuntimeError(f"{DEMO_EMAIL} already exists as {existing_demo.id}")

        demo_user.email = DEMO_EMAIL
        demo_user.full_name = DEMO_FULL_NAME
        demo_user.password_hash = hash_password(DEMO_PASSWORD)
        demo_user.role = Role.administrator
        demo_user.tenant_id = EURODRIVE_TENANT_ID
        demo_user.is_active = True

        # Ensure Anna/Maria can also be used for multi-seat demos
        for email, name, uid in (
            ("anna.kowalska@eurodrive.example", "Anna Kowalska", "a1111111-1111-4111-8111-111111111101"),
            ("maria.nowak@eurodrive.example", "Maria Nowak", "a1111111-1111-4111-8111-111111111102"),
        ):
            u = (await db.execute(select(User).where(User.id == uid).limit(1))).scalar_one_or_none()
            if u is None:
                continue
            u.email = email
            u.full_name = name
            u.password_hash = hash_password(DEMO_PASSWORD)
            u.is_active = True
            u.tenant_id = EURODRIVE_TENANT_ID

        # Scrub personal email from operating company contacts
        company = (
            await db.execute(select(Company).where(Company.id == OWN_COMPANY_ID).limit(1))
        ).scalar_one_or_none()
        if company is not None:
            company.contacts = {
                "primary": {"name": DEMO_FULL_NAME, "email": DEMO_EMAIL, "phone": "+48 61 222 0100"}
            }
            if company.email and "igor" in company.email.lower():
                company.email = DEMO_EMAIL

        # Candidate manager display labels still say "Igor"
        await db.execute(
            text(
                """
                UPDATE candidates
                SET manager = 'Adam'
                WHERE tenant_id = :tid AND manager = 'Igor'
                """
            ),
            {"tid": EURODRIVE_TENANT_ID},
        )

        # --- Personal workspace for real Igor account ---
        personal = (
            await db.execute(select(User).where(User.email == PERSONAL_EMAIL).limit(1))
        ).scalar_one_or_none()
        if personal is None:
            personal_tenant_id = str(uuid.uuid4())
            personal_user_id = str(uuid.uuid4())
            api_key = secrets_api_key()
            personal_tenant = Tenant(
                id=personal_tenant_id,
                name="Igor Tatarynovich",
                slug=f"igor-{personal_tenant_id[:8]}",
                api_key=api_key,
                is_active=True,
                type=TenantType.agency,
                status=TenantStatus.active,
                workspace_label="Igor Tatarynovich",
                description="Personal workspace (moved off shared EuroDrive demo).",
                settings={
                    "signup": {"source": "ops_migrate_from_shared_demo"},
                    "modules": dict((settings.get("modules") or {})),
                    "business_type": "agency",
                },
            )
            db.add(personal_tenant)
            db.add(
                TenantLicense(
                    id=str(uuid.uuid4()),
                    tenant_id=personal_tenant_id,
                    plan="team",
                    max_recruiters=25,
                    max_supervisors=10,
                    max_client_managers=5,
                    max_viewers=50,
                    max_storage_gb=100,
                    max_companies=10,
                    max_candidates_active=10000,
                    max_vacancies_active=500,
                    max_documents=50000,
                    max_public_portal_links=20,
                    expires_at=date(2030, 12, 31),
                    auto_renew=True,
                    notes="personal-after-shared-demo-split",
                )
            )
            prefs = dict(personal_preferences)
            prefs.pop("active_own_company_id", None)
            personal = User(
                id=personal_user_id,
                email=PERSONAL_EMAIL,
                password_hash=personal_password_hash,
                role=Role.administrator,
                full_name="Igor Tatarynovich",
                tenant_id=personal_tenant_id,
                is_active=True,
                preferences=prefs,
            )
            db.add(personal)
            await db.flush()
            await db.execute(
                user_memberships.insert().values(
                    id=str(uuid.uuid4()),
                    user_id=personal_user_id,
                    tenant_id=personal_tenant_id,
                    role=Role.administrator.value,
                    created_at=datetime.now(timezone.utc),
                )
            )
        else:
            # Email already taken somehow — leave as-is
            personal_tenant_id = personal.tenant_id
            personal_user_id = personal.id

        await db.commit()

        print(
            json.dumps(
                {
                    "ok": True,
                    "demo_tenant": {
                        "id": EURODRIVE_TENANT_ID,
                        "name": tenant.name,
                        "status": tenant.status.value if hasattr(tenant.status, "value") else str(tenant.status),
                        "plan": lic.plan,
                        "expires_at": str(lic.expires_at),
                        "login": DEMO_EMAIL,
                        "password": DEMO_PASSWORD,
                        "admin_name": DEMO_FULL_NAME,
                        "recruiters": [
                            "anna.kowalska@eurodrive.example",
                            "maria.nowak@eurodrive.example",
                        ],
                        "recruiter_password": DEMO_PASSWORD,
                    },
                    "personal": {
                        "email": PERSONAL_EMAIL,
                        "user_id": personal_user_id if personal else None,
                        "tenant_id": personal_tenant_id if personal else None,
                        "note": "same password as before the split",
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    await engine.dispose()


def secrets_api_key() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex[:16]


if __name__ == "__main__":
    asyncio.run(main())
