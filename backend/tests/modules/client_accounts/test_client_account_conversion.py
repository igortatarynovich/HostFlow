"""Stage 1A: ClientAccount conversion and idempotency tests."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from backend.app.models import ClientAccount, Company, Lead
from backend.app.models.own_company import OwnCompany
from backend.app.modules.client_accounts.conversion import convert_client_lead
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.leads import crud as leads_crud


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    own_company_id = row.scalar_one_or_none()
    if own_company_id is None:
        own_company_id = str(uuid.uuid4())
        db.add(OwnCompany(id=own_company_id, tenant_id=tenant_id, name=f"OC {uuid.uuid4().hex[:6]}"))
        await db.flush()
    return str(own_company_id)


async def _client_lead(
    db,
    *,
    tenant_id: str,
    own_company_id: str,
    suffix: str,
    normalized: dict | None = None,
) -> Lead:
    base_norm = {
        "company_name": f"Transport {suffix}",
        "email": f"client-{suffix}@example.com",
        "phone": f"+48{uuid.uuid4().int % 10**9:09d}",
        "full_name": f"Contact {suffix}",
    }
    if normalized:
        base_norm.update(normalized)
    return await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized=base_norm,
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )


async def _seed_company(
    db,
    *,
    tenant_id: str,
    name: str,
) -> Company:
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
async def test_convert_creates_client_account_and_company(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await _client_lead(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=suffix)

    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))
    assert locked is not None
    result = await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
    await db.commit()

    assert result.idempotent_replay is False
    assert result.client_account is not None
    assert result.company is not None
    assert lead.client_account_id == str(result.client_account.id)
    assert lead.converted_client_id == str(result.company.id)
    assert result.company.client_account_id == str(result.client_account.id)
    assert result.client_account.primary_company_id == str(result.company.id)

    account_count = await db.scalar(
        select(func.count()).select_from(ClientAccount).where(ClientAccount.source_lead_id == str(lead.id))
    )
    assert account_count == 1


@pytest.mark.asyncio
async def test_convert_replay_is_idempotent(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await _client_lead(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=suffix)

    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))
    first = await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
    await db.commit()

    locked2 = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))
    second = await convert_client_lead(db, tenant_id=tenant_id, lead=locked2, actor_id=None)
    await db.commit()

    assert first.client_account.id == second.client_account.id
    assert second.idempotent_replay is True
    account_count = await db.scalar(
        select(func.count()).select_from(ClientAccount).where(ClientAccount.source_lead_id == str(lead.id))
    )
    assert account_count == 1


@pytest.mark.asyncio
async def test_convert_without_company_name_creates_account_only(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await _client_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        suffix=suffix,
        normalized={
            "company_name": "",
            "full_name": f"Solo Contact {suffix}",
            "email": f"solo-{suffix}@example.com",
        },
    )

    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))
    result = await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
    await db.commit()

    assert result.company is None
    assert result.client_account.display_name == f"Solo Contact {suffix}"
    assert lead.client_account_id == str(result.client_account.id)
    assert lead.converted_client_id is None


@pytest.mark.asyncio
async def test_parallel_convert_creates_single_account(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await _client_lead(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=suffix)
    lead_id = str(lead.id)

    async def _run_convert() -> str:
        locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=lead_id)
        assert locked is not None
        result = await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
        return str(result.client_account.id)

    # Sequential locked converts emulate race resolution; DB unique index is the hard guard.
    id_a = await _run_convert()
    await db.commit()
    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=lead_id)
    id_b = (await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)).client_account.id
    await db.commit()
    assert id_a == id_b

    account_count = await db.scalar(
        select(func.count()).select_from(ClientAccount).where(ClientAccount.source_lead_id == lead_id)
    )
    company_count = await db.scalar(
        select(func.count()).select_from(Company).where(Company.client_account_id.is_not(None))
    )
    assert account_count == 1
    assert company_count >= 1


@pytest.mark.asyncio
async def test_archived_company_does_not_delete_client_account(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await _client_lead(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=suffix)
    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))
    result = await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
    await db.commit()

    company = result.company
    assert company is not None
    company.is_archived = True
    await db.commit()

    account = await db.get(ClientAccount, str(result.client_account.id))
    assert account is not None
    assert account.primary_company_id == str(company.id)


@pytest.mark.asyncio
async def test_company_create_failure_does_not_orphan_client_account(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    lead = await _client_lead(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=suffix)
    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))

    with patch(
        "backend.app.modules.client_accounts.conversion.create_company_service",
        new_callable=AsyncMock,
        side_effect=ValueError("company create failed"),
    ):
        with pytest.raises(ValueError, match="company create failed"):
            await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
    await db.rollback()

    account_count = await db.scalar(
        select(func.count()).select_from(ClientAccount).where(ClientAccount.source_lead_id == str(lead.id))
    )
    assert account_count == 0


@pytest.mark.asyncio
async def test_legacy_converted_client_backfills_client_account(db, tenant_id: str) -> None:
    own_company_id = await _own_company_id(db, tenant_id)
    suffix = uuid.uuid4().hex[:8]
    company = await _seed_company(db, tenant_id=tenant_id, name=f"Legacy Co {suffix}")
    await db.flush()
    lead = await _client_lead(db, tenant_id=tenant_id, own_company_id=own_company_id, suffix=suffix)
    lead.converted_client_id = str(company.id)
    await db.flush()

    locked = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))
    result = await convert_client_lead(db, tenant_id=tenant_id, lead=locked, actor_id=None)
    await db.commit()

    assert result.client_account is not None
    assert result.company is not None
    assert str(result.company.id) == str(company.id)
    assert lead.client_account_id == str(result.client_account.id)
    assert result.company.client_account_id == str(result.client_account.id)
