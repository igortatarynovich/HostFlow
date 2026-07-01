"""Requirement Rules Engine P1 — platform API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1, REQUIREMENT_RULES_V1


pytestmark = pytest.mark.anyio


async def _seed_entity_profiles(tenant_id: str) -> None:
    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
        except Exception as exc:
            pytest.skip(f"Entity Profile tables not available: {exc}")
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await session.commit()


@pytest.mark.asyncio
async def test_p1_api_get_requirement_rules_driver_ce(client: AsyncClient, manager_headers, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    resp = await client.get(
        f"/api/v1/platform/requirement-rules/{DRIVER_CE_PROFILE_CODE}",
        params={"context": "readiness"},
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["contract_version"] == REQUIREMENT_RULES_V1
    assert body["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert body["document_pack_code"] == "recruitment.driver_ce_documents"
    assert body["p1_sources_only"] is True
    rule_types = {row["rule_type"] for row in body["rules"]}
    assert "field_required" in rule_types
    assert "document_required" in rule_types


@pytest.mark.asyncio
async def test_p1_api_evaluate_driver_ce_not_satisfied(client: AsyncClient, manager_headers, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    resp = await client.post(
        "/api/v1/platform/requirement-rules/evaluate",
        headers=manager_headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "context": "readiness",
            "normalized_payload": {
                "recruitment.candidate.first_name": "Anna",
            },
            "documents": [],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["evaluation_version"] == REQUIREMENT_EVALUATION_V1
    assert body["satisfied"] is False
    assert body["blockers"]
    assert any(row.get("qualified_code") == "recruitment.candidate.contacts.phone" for row in body["blockers"] if row.get("qualified_code"))


@pytest.mark.asyncio
async def test_p1_api_evaluate_intake_no_document_rules(client: AsyncClient, manager_headers, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    resp = await client.post(
        "/api/v1/platform/requirement-rules/evaluate",
        headers=manager_headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "context": "intake",
            "normalized_payload": {
                "recruitment.candidate.first_name": "Anna",
                "recruitment.candidate.last_name": "Nowak",
                "recruitment.candidate.contacts.phone": "+48111222333",
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["required_documents"] == []
    assert body["satisfied"] is True


@pytest.mark.asyncio
async def test_p1_api_unknown_profile_404(client: AsyncClient, manager_headers, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    resp = await client.get(
        "/api/v1/platform/requirement-rules/recruitment.candidate.missing_profile",
        headers=manager_headers,
    )
    assert resp.status_code == 404, resp.text
