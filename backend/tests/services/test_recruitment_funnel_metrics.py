"""Tests for recruitment funnel resolver metrics (deprecation telemetry)."""

from __future__ import annotations

import uuid

import pytest

from backend.app.models.company import Company
from backend.app.models.funnel import Funnel
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.services.recruitment_funnel_metrics import (
    get_recruitment_funnel_metrics_snapshot,
    record_recruitment_funnel_analytics,
    reset_recruitment_funnel_metrics,
)
from backend.app.services.recruitment_funnel_resolver import resolve_recruitment_funnel


def _uid() -> str:
    return str(uuid.uuid4())


async def _seed_tenant(db, *, tenant_id: str | None = None) -> str:
    tid = tenant_id or _uid()
    suffix = tid.replace("-", "")[:10]
    db.add(
        Tenant(
            id=tid,
            name=f"Metrics Test {suffix}",
            slug=f"met-{suffix}",
            api_key=f"met-key-{suffix}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={"modules": {"recruitment": True, "candidates": True, "leads": True, "vacancies": True}},
        )
    )
    await db.flush()
    return tid


async def _seed_company(db, *, tenant_id: str) -> str:
    cid = _uid()
    db.add(Company(id=cid, tenant_id=tenant_id, name=f"Metrics Co {cid[:8]}"))
    await db.flush()
    return cid


async def _seed_funnel(
    db,
    *,
    tenant_id: str,
    company_id: str | None,
    is_default: bool = True,
) -> Funnel:
    funnel = Funnel(
        id=_uid(),
        tenant_id=tenant_id,
        company_id=company_id,
        module_key="recruitment",
        type="candidate",
        name="Company Default",
        is_default=is_default,
    )
    db.add(funnel)
    await db.flush()
    return funnel


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    reset_recruitment_funnel_metrics()
    yield
    reset_recruitment_funnel_metrics()


@pytest.mark.anyio
async def test_metrics_record_company_default_and_legacy(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await _seed_funnel(db, tenant_id=tenant_id, company_id=company_id)

    await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
    )

    snap = get_recruitment_funnel_metrics_snapshot()
    assert snap.total_resolves == 1
    assert snap.by_source.get("company_default") == 1
    assert snap.legacy_strangler_hits == 0


@pytest.mark.anyio
async def test_metrics_record_legacy_strangler(db) -> None:
    tenant_id = await _seed_tenant(db)
    company_id = await _seed_company(db, tenant_id=tenant_id)
    await _seed_funnel(
        db,
        tenant_id=tenant_id,
        company_id=None,
        is_default=True,
    )

    await resolve_recruitment_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        pipeline_type="candidate",
    )

    snap = get_recruitment_funnel_metrics_snapshot()
    assert snap.total_resolves == 1
    assert snap.by_source.get("legacy_tenant") == 1
    assert snap.legacy_strangler_hits == 1


def test_metrics_record_analytics_pipeline_scope() -> None:
    record_recruitment_funnel_analytics(pipeline_type="candidate", scope="recruitment_company")
    record_recruitment_funnel_analytics(pipeline_type="lead", scope="legacy_tenant")

    snap = get_recruitment_funnel_metrics_snapshot()
    assert snap.analytics_by_pipeline.get("candidate:recruitment_company") == 1
    assert snap.analytics_by_pipeline.get("lead:legacy_tenant") == 1
