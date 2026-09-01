"""Standalone employers must not enter handoff-client view."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from backend.app.models.tenant import Tenant, TenantLink, TenantStatus, TenantType
from backend.app.platform.next_action.setup_activation_policy import is_handler_blocked_for_guided_trial
from backend.app.services.handoff import is_client_tenant, is_client_tenant_for_list
from backend.tests.conftest import _set_tenant


def _uid() -> str:
    return str(uuid.uuid4())


@pytest_asyncio.fixture
async def class_db():
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        yield session
        await session.rollback()


async def _seed_tenant(db, *, tenant_type: TenantType) -> str:
    tid = _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"Classify {suffix}",
            slug=f"cl-{suffix}",
            api_key=f"cl-key-{suffix}",
            type=tenant_type,
            status=TenantStatus.trial,
            settings={"signup": {"source": "self_service"}},
        )
    )
    await db.flush()
    await _set_tenant(db, tid)
    return tid


@pytest.mark.anyio
async def test_standalone_employer_is_not_handoff_client(class_db) -> None:
    tid = await _seed_tenant(class_db, tenant_type=TenantType.company)
    assert await is_client_tenant(class_db, tid) is False
    assert await is_client_tenant_for_list(class_db, tid) is False


@pytest.mark.anyio
async def test_inbound_tenant_link_enables_handoff_client_view(class_db) -> None:
    client_tid = await _seed_tenant(class_db, tenant_type=TenantType.company)
    agency_tid = await _seed_tenant(class_db, tenant_type=TenantType.agency)
    class_db.add(
        TenantLink(
            id=_uid(),
            agency_tenant_id=agency_tid,
            client_tenant_id=client_tid,
            status="active",
        )
    )
    await class_db.flush()
    assert await is_client_tenant(class_db, client_tid) is True
    assert await is_client_tenant(class_db, agency_tid) is False


def test_guided_trial_does_not_block_settings() -> None:
    assert (
        is_handler_blocked_for_guided_trial(
            "/app/settings/integrations",
            tenant_status="trial",
        )
        is False
    )
