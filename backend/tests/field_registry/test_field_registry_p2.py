"""Field Registry P2 — effective layout read integration smoke (vacancy/client)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.field_registry.constants import (
    DEFAULT_CLIENT_LAYOUT_CODE,
    DEFAULT_VACANCY_LAYOUT_CODE,
    ENTITY_CLIENT,
    ENTITY_VACANCY,
)
from backend.app.field_registry.resolver import resolve_effective_card_layout
from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults


@pytest.mark.anyio
async def test_p2_effective_layout_smoke_vacancy_and_client(db) -> None:
    tenant_id = f"fr-p2-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    vacancy_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_VACANCY,
        layout_code=DEFAULT_VACANCY_LAYOUT_CODE,
        module="recruitment",
    )
    assert vacancy_layout["resolution_source"] != "not_found"
    assert vacancy_layout["layout_code"] == DEFAULT_VACANCY_LAYOUT_CODE
    assert any(row["qualified_code"] == "recruitment.vacancy.title" for row in vacancy_layout["fields"])
    assert any(section["code"] == "basic" for section in vacancy_layout["sections"])

    client_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_CLIENT,
        layout_code=DEFAULT_CLIENT_LAYOUT_CODE,
        module="crm",
    )
    assert client_layout["resolution_source"] != "not_found"
    assert client_layout["layout_code"] == DEFAULT_CLIENT_LAYOUT_CODE
    assert client_layout["fields"]
    assert any(section["code"] == "basic" for section in client_layout["sections"])
