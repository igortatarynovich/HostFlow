from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from backend.app.db.session import async_session_maker
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLicense, TenantStatus, TenantType
from backend.app.models.user import Role as UserRole, User
from backend.app.modules.companies import crud, schemas
from backend.app.modules.companies.crud import OperatingCompanyLimitReached
from backend.app.services.operating_company_slots import get_operating_company_slots


async def _set_tenant_context(db, tenant_id: str) -> None:
    db.info["tenant_id"] = tenant_id
    await db.execute(text("SELECT set_config('app.tenant_id', :tenant_id, false)"), {"tenant_id": tenant_id})


@pytest.mark.anyio
async def test_operating_company_slots_buy_create_downgrade_flow() -> None:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    company_ids: list[str] = []
    async with async_session_maker() as db:
        tenant = Tenant(
            id=tenant_id,
            name=f"A6 S7 Tenant {tenant_id[:8]}",
            slug=f"a6-s7-{tenant_id[:8]}",
            api_key=f"a6-s7-{uuid4().hex}",
            is_active=True,
            status=TenantStatus.active,
            type=TenantType.agency,
            settings={"billing": {"subscription": {"plan_code": "starter", "extra_operating_company_slots": 0}}},
        )
        license_row = TenantLicense(
            id=str(uuid4()),
            tenant_id=tenant_id,
            plan="starter",
            max_companies=1,
        )
        user = User(
            id=user_id,
            email=f"a6-s7-{tenant_id[:8]}@example.com",
            password_hash="x",
            role=UserRole.administrator,
            tenant_id=tenant_id,
            is_active=True,
            deleted_at=None,
        )
        db.add_all([tenant, license_row, user])
        await db.commit()

        try:
            await _set_tenant_context(db, tenant_id)

            initial = await get_operating_company_slots(db, tenant_id)
            assert initial.included_limit == 1
            assert initial.extra_slots == 0
            assert initial.effective_limit == 1
            assert initial.used == 0

            first = await crud.create_company(
                db,
                schemas.CompanyCreate(
                    name="A6 S7 Operating #1",
                    company_type="services",
                    company_role="operating",
                ),
                actor_user_id=user_id,
            )
            company_ids.append(str(first.id))
            after_first = await get_operating_company_slots(db, tenant_id)
            assert after_first.used == 1
            assert after_first.available == 0

            with pytest.raises(OperatingCompanyLimitReached) as blocked_before_buy:
                await crud.create_company(
                    db,
                    schemas.CompanyCreate(
                        name="A6 S7 Operating blocked before add-on",
                        company_type="services",
                        company_role="operating",
                    ),
                    actor_user_id=user_id,
                )
            assert blocked_before_buy.value.effective_limit == 1
            assert blocked_before_buy.value.used == 1

            tenant.settings = {
                "billing": {"subscription": {"plan_code": "starter", "extra_operating_company_slots": 1}}
            }
            db.add(tenant)
            await db.commit()

            after_buy = await get_operating_company_slots(db, tenant_id)
            assert after_buy.extra_slots == 1
            assert after_buy.effective_limit == 2
            assert after_buy.available == 1

            await crud.create_company(
                db,
                schemas.CompanyCreate(
                    name="A6 S7 Operating #2",
                    company_type="services",
                    company_role="operating",
                ),
                actor_user_id=user_id,
            )
            second = (
                await db.execute(
                    select(Company)
                    .where(Company.tenant_id == tenant_id)
                    .where(Company.name == "A6 S7 Operating #2")
                    .limit(1)
                )
            ).scalar_one()
            company_ids.append(str(second.id))
            after_second = await get_operating_company_slots(db, tenant_id)
            assert after_second.used == 2
            assert after_second.available == 0

            tenant.settings = {
                "billing": {"subscription": {"plan_code": "starter", "extra_operating_company_slots": 0}}
            }
            db.add(tenant)
            await db.commit()

            after_downgrade = await get_operating_company_slots(db, tenant_id)
            assert after_downgrade.extra_slots == 0
            assert after_downgrade.effective_limit == 1
            assert after_downgrade.used == 2
            assert after_downgrade.available == 0

            with pytest.raises(OperatingCompanyLimitReached) as blocked_after_downgrade:
                await crud.create_company(
                    db,
                    schemas.CompanyCreate(
                        name="A6 S7 Operating blocked after downgrade",
                        company_type="services",
                        company_role="operating",
                    ),
                    actor_user_id=user_id,
                )
            assert blocked_after_downgrade.value.effective_limit == 1
            assert blocked_after_downgrade.value.used == 2

            persisted = (
                await db.execute(
                    select(Company).where(Company.tenant_id == tenant_id).order_by(Company.created_at.asc())
                )
            ).scalars().all()
            assert len(persisted) == 2
            assert {str(item.id) for item in persisted} == set(company_ids)
        finally:
            if company_ids:
                await db.execute(delete(Company).where(Company.id.in_(company_ids)))
            await db.execute(delete(User).where(User.id == user_id))
            await db.execute(delete(TenantLicense).where(TenantLicense.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
