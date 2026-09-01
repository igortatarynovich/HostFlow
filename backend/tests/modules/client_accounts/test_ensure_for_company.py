"""Operator Add Client must produce a ClientAccount (campaigns target accounts, not companies)."""

from __future__ import annotations

import uuid

import pytest

from backend.app.models import ClientAccount, Company
from backend.app.modules.client_accounts.ensure_for_company import (
    ensure_manual_client_account_for_company,
    ensure_manual_client_accounts_for_local_client_companies,
    is_local_client_company,
)


async def _seed_company(db, *, tenant_id: str, name: str, role: str = "client") -> Company:
    company = Company(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        extra={"company_role": role},
        client_stage="negotiation",
    )
    db.add(company)
    await db.flush()
    return company


@pytest.mark.asyncio
async def test_ensure_creates_account_and_is_idempotent(db, tenant_id: str) -> None:
    company = await _seed_company(db, tenant_id=tenant_id, name="Rock Cargo")
    actor = str(uuid.uuid4())
    first = await ensure_manual_client_account_for_company(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor,
        company=company,
    )
    await db.flush()
    assert first.display_name == "Rock Cargo"
    assert first.origin_type == "manual_creation"
    assert first.primary_company_id == str(company.id)
    assert first.status == "prospect"
    assert str(company.client_account_id) == str(first.id)

    second = await ensure_manual_client_account_for_company(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor,
        company=company,
    )
    assert str(second.id) == str(first.id)


@pytest.mark.asyncio
async def test_ensure_skips_operating_company_in_batch(db, tenant_id: str) -> None:
    client = await _seed_company(db, tenant_id=tenant_id, name="POLTRAKT")
    operating = await _seed_company(db, tenant_id=tenant_id, name="Focus Personnel", role="operating")
    assert is_local_client_company(client) is True
    assert is_local_client_company(operating) is False

    rows = await ensure_manual_client_accounts_for_local_client_companies(
        db,
        tenant_id=tenant_id,
        actor_user_id=str(uuid.uuid4()),
    )
    await db.flush()
    names = {row.display_name for row in rows}
    assert "POLTRAKT" in names
    assert "Focus Personnel" not in names
    assert operating.client_account_id is None


@pytest.mark.asyncio
async def test_ensure_does_not_write_foreign_company_link(db, tenant_id: str) -> None:
    foreign = await _seed_company(db, tenant_id=str(uuid.uuid4()), name="Envo")
    account = await ensure_manual_client_account_for_company(
        db,
        tenant_id=tenant_id,
        actor_user_id=str(uuid.uuid4()),
        company=foreign,
        reason="operator_link_employer_tenant",
        link_primary_company=False,
    )
    await db.flush()
    assert account.tenant_id == tenant_id
    assert account.primary_company_id is None
    assert foreign.client_account_id is None
    loaded = await db.get(ClientAccount, account.id)
    assert loaded is not None
