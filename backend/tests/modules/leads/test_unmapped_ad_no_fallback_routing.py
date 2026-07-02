"""Unmapped Meta ad_id must not auto-attach to an arbitrary open vacancy."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.modules.leads import service as leads_service
from backend.app.modules.leads.service._helpers import (
    resolve_vacancy_for_lead_processing,
    unresolved_vacancy_routing_error_code,
)
from backend.tests.conftest import DEFAULT_TENANT_ID, _set_tenant


@pytest.mark.asyncio
async def test_unresolved_vacancy_routing_error_code_for_unmapped_ad() -> None:
    assert unresolved_vacancy_routing_error_code({"ad_id": 120252550967070547}) == "AD_NOT_MAPPED"
    assert unresolved_vacancy_routing_error_code({}) == "VACANCY_NOT_RESOLVED"
    assert (
        unresolved_vacancy_routing_error_code({"ad_id": 1, "vacancy_id": "00000000-0000-0000-0000-000000000001"})
        == "VACANCY_NOT_RESOLVED"
    )


@pytest.mark.asyncio
async def test_resolve_vacancy_for_lead_processing_skips_last_resort_fallback(db) -> None:
    tenant_id = DEFAULT_TENANT_ID
    normalized: dict = {"ad_id": 999999999999999999, "phone": "+48123456789"}
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        vacancy, fit_status, fit_reasons = await resolve_vacancy_for_lead_processing(
            session,
            tenant_id=tenant_id,
            normalized=normalized,
            tenant_settings={},
            source="meta",
        )
    assert vacancy is None
    assert fit_status is None
    assert fit_reasons == []
    assert "vacancy_routing_fallback_v1" not in normalized


@pytest.mark.asyncio
async def test_process_normalized_lead_unmapped_ad_stays_needs_routing(db) -> None:
    tenant_id = DEFAULT_TENANT_ID
    external_id = f"unmapped-ad-{uuid.uuid4().hex}"
    unmapped_ad_id = 999999999999999998

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        await session.execute(
            sa.text(
                """
                INSERT INTO meta_lead_settings (tenant_id, auto_create_enabled, leads_processing_mode_v1)
                VALUES (:tenant_id, true, 'automatic')
                ON CONFLICT (tenant_id) DO UPDATE SET
                    auto_create_enabled = EXCLUDED.auto_create_enabled,
                    leads_processing_mode_v1 = EXCLUDED.leads_processing_mode_v1
                """
            ),
            {"tenant_id": tenant_id},
        )
        await session.commit()

    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            result = await leads_service.process_normalized_lead(
                session,
                tenant_id=tenant_id,
                payload={"id": external_id, "form_id": "TEST-FORM-UNMAPPED-AD", "page_id": "TEST-PAGE"},
                normalized={
                    "ad_id": unmapped_ad_id,
                    "form_id": "TEST-FORM-UNMAPPED-AD",
                    "page_id": "TEST-PAGE",
                    "phone": "+48987654321",
                    "full_name": "Unmapped Ad Test",
                    "leads_processing_mode_v1": "automatic",
                },
                source="meta",
                external_id=external_id,
            )
            await session.commit()

        assert result.status == "needs_routing"
        assert result.error == "AD_NOT_MAPPED"
        assert result.vacancy_id is None
        assert result.candidate_id is None

        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            row = await session.execute(
                sa.text(
                    """
                    SELECT status, error, vacancy_id, candidate_id, normalized->'vacancy_routing_fallback_v1'
                    FROM leads
                    WHERE external_id = :external_id
                    LIMIT 1
                    """
                ),
                {"external_id": external_id},
            )
            status, error, vacancy_id, candidate_id, fallback = row.fetchone()
            assert status == "needs_routing"
            assert error == "AD_NOT_MAPPED"
            assert vacancy_id is None
            assert candidate_id is None
            assert fallback is None
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(
                sa.text("DELETE FROM leads WHERE external_id = :external_id"),
                {"external_id": external_id},
            )
            await session.commit()
