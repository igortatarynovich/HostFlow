"""Intake routing foundation schema constraints and tenant isolation (PR-2)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.db.session import async_session_maker
from backend.app.models import IntakeSourceBinding, IntakeSourceProfile, OwnCompany
from backend.app.modules.intake_routing import crud
from backend.app.modules.intake_routing.crud import IntakeRoutingValidationError

TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"


async def _db_role_bypasses_rls(session) -> bool:
    if session.get_bind().dialect.name != "postgresql":
        return True
    row = (
        await session.execute(
            text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
        )
    ).one_or_none()
    return bool(row and row[0])


async def _ensure_own_company(db, *, tenant_id: str = TENANT_ID) -> str:
    oc_id = str(uuid.uuid4())
    db.add(
        OwnCompany(
            id=oc_id,
            tenant_id=tenant_id,
            name=f"Intake OC {oc_id[:8]}",
        )
    )
    await db.flush()
    return oc_id


async def _create_profile(
    db,
    *,
    code: str,
    own_company_id: str,
    is_active: bool = True,
    tenant_id: str = TENANT_ID,
) -> IntakeSourceProfile:
    return await crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=code,
        name=f"Profile {code}",
        own_company_id=own_company_id,
        provider="meta",
        channel="paid",
        route_intent="sales_inquiry",
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_profile_code_unique_per_tenant(db) -> None:
    oc_id = await _ensure_own_company(db)
    code = f"meta-b2b-{uuid.uuid4().hex[:8]}"

    await _create_profile(db, code=code, own_company_id=oc_id)

    with pytest.raises(IntakeRoutingValidationError, match="unique per tenant"):
        await _create_profile(db, code=code, own_company_id=oc_id)


@pytest.mark.asyncio
async def test_binding_unique_per_provider_external_key(db) -> None:
    oc_id = await _ensure_own_company(db)
    profile = await _create_profile(db, code=f"p-{uuid.uuid4().hex[:8]}", own_company_id=oc_id)
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"

    await crud.create_binding(
        db,
        tenant_id=TENANT_ID,
        intake_source_profile_id=profile.id,
        provider="meta",
        external_key=external_key,
    )

    with pytest.raises(IntakeRoutingValidationError, match="unique per tenant"):
        await crud.create_binding(
            db,
            tenant_id=TENANT_ID,
            intake_source_profile_id=profile.id,
            provider="meta",
            external_key=external_key,
        )


@pytest.mark.asyncio
async def test_inactive_profile_does_not_break_schema(db) -> None:
    oc_id = await _ensure_own_company(db)
    code = f"inactive-{uuid.uuid4().hex[:8]}"
    profile = await _create_profile(db, code=code, own_company_id=oc_id, is_active=False)

    binding = await crud.create_binding(
        db,
        tenant_id=TENANT_ID,
        intake_source_profile_id=profile.id,
        provider="meta",
        external_key=f"form_id:{uuid.uuid4().hex[:12]}",
        is_active=False,
    )
    await db.commit()

    loaded = await crud.get_profile_by_code(db, tenant_id=TENANT_ID, code=code)
    assert loaded is not None
    assert loaded.is_active is False
    assert binding.is_active is False


@pytest.mark.asyncio
async def test_binding_rejects_profile_from_other_tenant(db) -> None:
    oc_id = await _ensure_own_company(db)
    profile = await _create_profile(db, code=f"cross-{uuid.uuid4().hex[:8]}", own_company_id=oc_id)

    with pytest.raises(IntakeRoutingValidationError, match="not found"):
        await crud.create_binding(
            db,
            tenant_id=OTHER_TENANT_ID,
            intake_source_profile_id=profile.id,
            provider="meta",
            external_key=f"form_id:{uuid.uuid4().hex[:12]}",
        )


@pytest.mark.asyncio
async def test_rls_hides_other_tenant_profiles(db) -> None:
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("RLS tenant isolation requires PostgreSQL")
    if await _db_role_bypasses_rls(db):
        pytest.skip("current DB role bypasses RLS (dev superuser); policies exist but are not enforced")

    oc_id = await _ensure_own_company(db)
    code = f"rls-{uuid.uuid4().hex[:8]}"
    profile = await _create_profile(db, code=code, own_company_id=oc_id)
    await db.commit()

    async with async_session_maker() as other_session:
        await other_session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": OTHER_TENANT_ID},
        )
        rows = (
            await other_session.execute(
                select(IntakeSourceProfile).where(IntakeSourceProfile.id == profile.id)
            )
        ).scalars().all()
        assert rows == []

        bindings = (
            await other_session.execute(
                select(IntakeSourceBinding).where(
                    IntakeSourceBinding.intake_source_profile_id == profile.id
                )
            )
        ).scalars().all()
        assert bindings == []
