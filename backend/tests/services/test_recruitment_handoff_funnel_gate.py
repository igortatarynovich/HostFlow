"""Handoff-on companies require ready_for_handoff on assigned candidate funnels."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant, TenantLink, TenantStatus, TenantType
from backend.app.models.vacancy import Vacancy
from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY
from backend.app.services.recruitment_handoff_funnel_gate import (
    HandoffFunnelGateError,
    READY_FOR_HANDOFF_STAGE_CODE,
    ensure_can_drop_ready_for_handoff_from_funnel,
    ensure_can_enable_handoff_for_company,
    ensure_candidate_funnel_allows_company_handoff,
    ensure_vacancy_funnel_assignment_allowed,
    funnel_codes_include_ready_for_handoff,
)
from backend.tests.conftest import _set_tenant


def _uid() -> str:
    return str(uuid.uuid4())


def test_funnel_codes_include_ready_for_handoff() -> None:
    assert funnel_codes_include_ready_for_handoff(["new", "ready_for_handoff"]) is True
    assert funnel_codes_include_ready_for_handoff(["Ready_For_Handoff"]) is True
    assert funnel_codes_include_ready_for_handoff(["new", "employed"]) is False
    assert funnel_codes_include_ready_for_handoff([]) is False


@pytest_asyncio.fixture
async def gate_db():
    """Session without suite bootstrap — these tests insert their own tenant rows."""
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        yield session
        await session.rollback()


def _uid() -> str:
    return str(uuid.uuid4())


def test_funnel_codes_include_ready_for_handoff() -> None:
    assert funnel_codes_include_ready_for_handoff(["new", "ready_for_handoff"]) is True
    assert funnel_codes_include_ready_for_handoff(["Ready_For_Handoff"]) is True
    assert funnel_codes_include_ready_for_handoff(["new", "employed"]) is False
    assert funnel_codes_include_ready_for_handoff([]) is False


async def _seed_tenant(db) -> str:
    tid = _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"Handoff Gate {suffix}",
            slug=f"hg-{suffix}",
            api_key=f"hg-key-{suffix}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={"modules": {"recruitment": True, "candidates": True}},
        )
    )
    await db.flush()
    await _set_tenant(db, tid)
    return tid


async def _seed_company(db, *, tenant_id: str) -> str:
    cid = _uid()
    db.add(Company(id=cid, tenant_id=tenant_id, name=f"Client {cid[:8]}"))
    await db.flush()
    return cid


async def _seed_funnel(
    db,
    *,
    tenant_id: str,
    company_id: str,
    codes: list[str],
    name: str = "Pipeline",
) -> Funnel:
    funnel = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key=RECRUITMENT_MODULE_KEY,
        type="candidate",
        name=name,
        is_default=True,
    )
    db.add(funnel)
    await db.flush()
    for order, code in enumerate(codes):
        db.add(
            FunnelStage(
                id=_uid(),
                funnel_id=funnel.id,
                code=code,
                label=code,
                order=order,
            )
        )
    await db.flush()
    return funnel


async def _seed_link(db, *, tenant_id: str, company_id: str, enabled: bool) -> TenantLink:
    link = TenantLink(
        id=_uid(),
        agency_tenant_id=tenant_id,
        client_company_id=company_id,
        status="active",
        features_json={"handoff_enabled": enabled},
    )
    db.add(link)
    await db.flush()
    return link


async def _seed_vacancy(db, *, tenant_id: str, company_id: str, funnel_id: str | None) -> Vacancy:
    vacancy = Vacancy(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        title="Driver",
        funnel_id=funnel_id,
    )
    db.add(vacancy)
    await db.flush()
    return vacancy


@pytest.mark.anyio
async def test_assignment_allowed_when_handoff_off(gate_db) -> None:
    tenant_id = await _seed_tenant(gate_db)
    company_id = await _seed_company(gate_db, tenant_id=tenant_id)
    funnel = await _seed_funnel(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_id,
        codes=["new", "employed"],
        name="Rekrutacja",
    )
    await _seed_link(gate_db, tenant_id=tenant_id, company_id=company_id, enabled=False)
    await gate_db.flush()

    await ensure_candidate_funnel_allows_company_handoff(
        gate_db, tenant_id=tenant_id, company_id=company_id, funnel_id=funnel.id
    )


@pytest.mark.anyio
async def test_assignment_blocked_when_handoff_on_and_funnel_lacks_ready(gate_db) -> None:
    tenant_id = await _seed_tenant(gate_db)
    company_id = await _seed_company(gate_db, tenant_id=tenant_id)
    funnel = await _seed_funnel(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_id,
        codes=["new", "employed"],
        name="Rekrutacja",
    )
    await _seed_link(gate_db, tenant_id=tenant_id, company_id=company_id, enabled=True)
    await gate_db.flush()

    with pytest.raises(HandoffFunnelGateError, match=READY_FOR_HANDOFF_STAGE_CODE):
        await ensure_vacancy_funnel_assignment_allowed(
            gate_db,
            tenant_id=tenant_id,
            company_id=company_id,
            funnel_id=funnel.id,
        )


@pytest.mark.anyio
async def test_assignment_allowed_when_handoff_on_and_funnel_has_ready(gate_db) -> None:
    tenant_id = await _seed_tenant(gate_db)
    company_id = await _seed_company(gate_db, tenant_id=tenant_id)
    funnel = await _seed_funnel(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_id,
        codes=["new", "ready_for_handoff", "rejected"],
    )
    await _seed_link(gate_db, tenant_id=tenant_id, company_id=company_id, enabled=True)
    await gate_db.flush()

    await ensure_vacancy_funnel_assignment_allowed(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_id,
        funnel_id=funnel.id,
    )


@pytest.mark.anyio
async def test_enable_handoff_blocked_when_assigned_funnel_lacks_ready(gate_db) -> None:
    tenant_id = await _seed_tenant(gate_db)
    company_id = await _seed_company(gate_db, tenant_id=tenant_id)
    funnel = await _seed_funnel(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_id,
        codes=["new", "employed"],
        name="Rekrutacja",
    )
    await _seed_vacancy(gate_db, tenant_id=tenant_id, company_id=company_id, funnel_id=funnel.id)
    await gate_db.flush()

    with pytest.raises(HandoffFunnelGateError, match="Rekrutacja"):
        await ensure_can_enable_handoff_for_company(
            gate_db, tenant_id=tenant_id, company_id=company_id
        )


@pytest.mark.anyio
async def test_enable_handoff_allowed_when_no_assigned_funnels(gate_db) -> None:
    tenant_id = await _seed_tenant(gate_db)
    company_id = await _seed_company(gate_db, tenant_id=tenant_id)
    await _seed_funnel(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_id,
        codes=["new", "employed"],
        name="Unused",
    )
    await gate_db.flush()

    await ensure_can_enable_handoff_for_company(
        gate_db, tenant_id=tenant_id, company_id=company_id
    )


@pytest.mark.anyio
async def test_cannot_drop_ready_for_handoff_while_handoff_on(gate_db) -> None:
    tenant_id = await _seed_tenant(gate_db)
    company_id = await _seed_company(gate_db, tenant_id=tenant_id)
    funnel = await _seed_funnel(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_id,
        codes=["new", "ready_for_handoff"],
    )
    await _seed_link(gate_db, tenant_id=tenant_id, company_id=company_id, enabled=True)
    await gate_db.flush()

    with pytest.raises(HandoffFunnelGateError, match=READY_FOR_HANDOFF_STAGE_CODE):
        await ensure_can_drop_ready_for_handoff_from_funnel(
            gate_db,
            tenant_id=tenant_id,
            funnel=funnel,
            remaining_codes=["new"],
        )


@pytest.mark.anyio
async def test_sibling_company_handoff_does_not_block_assignment(gate_db) -> None:
    tenant_id = await _seed_tenant(gate_db)
    company_a = await _seed_company(gate_db, tenant_id=tenant_id)
    company_b = await _seed_company(gate_db, tenant_id=tenant_id)
    funnel_a = await _seed_funnel(
        gate_db,
        tenant_id=tenant_id,
        company_id=company_a,
        codes=["new", "employed"],
        name="Employment",
    )
    await _seed_link(gate_db, tenant_id=tenant_id, company_id=company_b, enabled=True)
    await gate_db.flush()

    await ensure_candidate_funnel_allows_company_handoff(
        gate_db, tenant_id=tenant_id, company_id=company_a, funnel_id=funnel_a.id
    )
