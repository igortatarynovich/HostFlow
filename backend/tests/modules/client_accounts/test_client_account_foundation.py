"""Stage 1A PR-1: ClientAccount foundation unit tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.app.models import ClientAccount
from backend.app.models.own_company import OwnCompany
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.client_accounts.schemas import ClientAccountCreate, ClientAccountUpdate
from backend.app.modules.client_accounts.service import (
    create_client_account_service,
    get_client_account_or_404,
    update_client_account_service,
)
from backend.app.models import Company


async def _seed_company(db, *, tenant_id: str, name: str) -> Company:
    company = Company(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        party_business_roles="service_client",
        client_stage="lead_converted",
    )
    db.add(company)
    await db.flush()
    return company


@pytest.mark.asyncio
async def test_cross_tenant_company_link_forbidden(db, tenant_id: str) -> None:
    other_tenant = str(uuid.uuid4())
    suffix = uuid.uuid4().hex[:8]
    foreign_company = await _seed_company(db, tenant_id=other_tenant, name=f"Foreign {suffix}")

    with pytest.raises(HTTPException) as exc_info:
        await create_client_account_service(
            db,
            tenant_id=tenant_id,
            data=ClientAccountCreate(
                display_name="Blocked link",
                primary_company_id=str(foreign_company.id),
            ),
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_client_account_crud_service(db, tenant_id: str) -> None:
    created = await create_client_account_service(
        db,
        tenant_id=tenant_id,
        data=ClientAccountCreate(display_name="Manual Account", status="prospect"),
    )
    await db.commit()

    loaded = await get_client_account_or_404(db, tenant_id=tenant_id, account_id=str(created.id))
    assert loaded.display_name == "Manual Account"

    updated = await update_client_account_service(
        db,
        tenant_id=tenant_id,
        account_id=str(created.id),
        data=ClientAccountUpdate(display_name="Updated Account", status="active"),
    )
    await db.commit()
    assert updated.display_name == "Updated Account"
    assert updated.status == "active"

    items, total = await account_crud.list_client_accounts(db, tenant_id=tenant_id, status="active")
    assert total >= 1
    assert any(str(row.id) == str(created.id) for row in items)

    count = await db.scalar(
        select(func.count()).select_from(ClientAccount).where(ClientAccount.tenant_id == tenant_id)
    )
    assert int(count or 0) >= 1
