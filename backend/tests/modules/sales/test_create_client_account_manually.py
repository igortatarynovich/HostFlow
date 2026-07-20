"""Origins v1 — create_client_account_manually (Stage 2 backend contract)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from backend.app.models import ClientAccount
from backend.app.models.own_company import OwnCompany
from backend.app.modules.client_accounts.schemas import ClientAccountCreate
from backend.app.modules.sales.services.create_client_account_manually import (
    ORIGIN_MANUAL_CREATION,
    ManualClientAccountDuplicateError,
    ManualClientAccountError,
    create_client_account_manually,
)


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


@pytest.mark.asyncio
async def test_manual_create_stamps_origin_and_never_sets_source_lead(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    actor = str(uuid.uuid4())
    result = await create_client_account_manually(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        actor_user_id=actor,
        display_name="Acme Manual Co",
        idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
        reason="operator intake",
    )
    await db.commit()

    account = result.account
    assert result.origin_type == ORIGIN_MANUAL_CREATION
    assert result.idempotent_replay is False
    assert account.origin_type == ORIGIN_MANUAL_CREATION
    assert account.creation_ref == result.creation_ref
    assert account.source_lead_id is None
    assert account.creation_origin_v1 is not None
    assert account.creation_origin_v1["origin_type"] == ORIGIN_MANUAL_CREATION
    assert account.creation_origin_v1["actor_user_id"] == actor
    assert account.creation_origin_v1["tenant_id"] == tenant_id
    assert account.creation_origin_v1["own_company_id"] == oc
    assert account.creation_origin_v1["creation_ref"] == result.creation_ref
    assert account.creation_origin_v1["idempotency_key"] == result.idempotency_key
    assert account.creation_origin_v1["reason"] == "operator intake"
    assert "created_at" in account.creation_origin_v1


@pytest.mark.asyncio
async def test_manual_create_idempotent_replay(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    key = f"ik-{uuid.uuid4().hex[:12]}"
    first = await create_client_account_manually(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        actor_user_id=str(uuid.uuid4()),
        display_name="Idempotent Co",
        idempotency_key=key,
    )
    await db.flush()
    second = await create_client_account_manually(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        actor_user_id=str(uuid.uuid4()),
        display_name="Idempotent Co",
        idempotency_key=key,
    )
    assert second.idempotent_replay is True
    assert str(second.account.id) == str(first.account.id)
    count = len(
        (
            await db.execute(
                select(ClientAccount).where(
                    ClientAccount.tenant_id == tenant_id,
                    ClientAccount.idempotency_key == key,
                )
            )
        )
        .scalars()
        .all()
    )
    assert count == 1


@pytest.mark.asyncio
async def test_manual_create_duplicate_fail_closed_without_force(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    await create_client_account_manually(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        actor_user_id=str(uuid.uuid4()),
        display_name="Dup Name LLC",
        idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
    )
    await db.flush()

    with pytest.raises(ManualClientAccountDuplicateError) as exc_info:
        await create_client_account_manually(
            db,
            tenant_id=tenant_id,
            own_company_id=oc,
            actor_user_id=str(uuid.uuid4()),
            display_name="  dup name llc  ",
            idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
        )
    assert exc_info.value.reason == "duplicate_match_requires_decision"
    assert len(exc_info.value.candidates) >= 1


@pytest.mark.asyncio
async def test_manual_create_force_requires_create_new_decision(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    await create_client_account_manually(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        actor_user_id=str(uuid.uuid4()),
        display_name="Force Co",
        idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
    )
    await db.flush()

    with pytest.raises(ManualClientAccountError) as exc_info:
        await create_client_account_manually(
            db,
            tenant_id=tenant_id,
            own_company_id=oc,
            actor_user_id=str(uuid.uuid4()),
            display_name="Force Co",
            idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
            force_create=True,
        )
    assert exc_info.value.reason == "missing_duplicate_decision"

    created = await create_client_account_manually(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        actor_user_id=str(uuid.uuid4()),
        display_name="Force Co",
        idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
        force_create=True,
        duplicate_decision={"action": "create_new"},
    )
    assert created.idempotent_replay is False
    assert created.account.origin_type == ORIGIN_MANUAL_CREATION
    assert created.account.creation_origin_v1["duplicate_decision"]["action"] == "create_new"


@pytest.mark.asyncio
async def test_manual_create_open_existing_and_cancel(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    first = await create_client_account_manually(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        actor_user_id=str(uuid.uuid4()),
        display_name="Decision Co",
        idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
    )
    await db.flush()

    with pytest.raises(ManualClientAccountError) as open_exc:
        await create_client_account_manually(
            db,
            tenant_id=tenant_id,
            own_company_id=oc,
            actor_user_id=str(uuid.uuid4()),
            display_name="Decision Co",
            idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
            force_create=True,
            duplicate_decision={
                "action": "open_existing",
                "client_account_id": str(first.account.id),
            },
        )
    assert open_exc.value.reason == "open_existing_required"

    with pytest.raises(ManualClientAccountError) as cancel_exc:
        await create_client_account_manually(
            db,
            tenant_id=tenant_id,
            own_company_id=oc,
            actor_user_id=str(uuid.uuid4()),
            display_name="Decision Co",
            idempotency_key=f"ik-{uuid.uuid4().hex[:12]}",
            force_create=True,
            duplicate_decision={"action": "cancel"},
        )
    assert cancel_exc.value.reason == "duplicate_cancelled"


@pytest.mark.asyncio
async def test_manual_create_rejects_missing_actor(db, tenant_id: str) -> None:
    with pytest.raises(ManualClientAccountError) as exc_info:
        await create_client_account_manually(
            db,
            tenant_id=tenant_id,
            own_company_id=None,
            actor_user_id="  ",
            display_name="No Actor",
        )
    assert exc_info.value.reason == "missing_actor"


def test_schema_rejects_source_lead_id_on_manual_create() -> None:
    with pytest.raises(ValidationError):
        ClientAccountCreate(display_name="X", source_lead_id=str(uuid.uuid4()))
