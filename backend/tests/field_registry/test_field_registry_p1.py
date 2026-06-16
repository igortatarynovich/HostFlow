"""Field Registry P1 — registry schema, seed, read API, read-only resolver."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text

from backend.app.field_registry.constants import (
    DEFAULT_CANDIDATE_LAYOUT_CODE,
    DEFAULT_CLIENT_LAYOUT_CODE,
    DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
    DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
    DEFAULT_VACANCY_LAYOUT_CODE,
    ENTITY_CANDIDATE,
    ENTITY_CLIENT,
    ENTITY_FLEET_VEHICLE,
    ENTITY_HR_EMPLOYEE,
    ENTITY_VACANCY,
)
from backend.app.field_registry.manifests.fleet import fleet_module_manifest
from backend.app.field_registry.manifests.hr import hr_module_manifest
from backend.app.field_registry.manifests.recruitment import recruitment_module_manifest
from backend.app.field_registry.registry import FieldRegistry
from backend.app.field_registry.resolver import list_canonical_fields_for_scope, resolve_effective_card_layout
from backend.app.field_registry.seed import ensure_platform_field_registry_catalog, ensure_tenant_field_registry_defaults
from backend.app.models.field_registry import (
    FrCanonicalField,
    FrCardLayoutField,
    FrCardLayoutProfile,
    PLATFORM_TENANT_SCOPE,
    REGISTRY_STATUS_ACTIVE,
)


def test_p1_recruitment_manifest_declares_baseline_entities() -> None:
    manifest = recruitment_module_manifest()
    entity_types = {row["entity_type"] for row in manifest["canonical_fields"]}
    assert ENTITY_CANDIDATE in entity_types
    assert ENTITY_VACANCY in entity_types
    layout_codes = {row["code"] for row in manifest["card_layouts"]}
    assert DEFAULT_CANDIDATE_LAYOUT_CODE in layout_codes
    assert DEFAULT_VACANCY_LAYOUT_CODE in layout_codes


def test_p6_hr_and_fleet_manifests_declare_baseline_entities() -> None:
    hr_manifest = hr_module_manifest()
    fleet_manifest = fleet_module_manifest()

    hr_codes = {row["qualified_code"] for row in hr_manifest["canonical_fields"]}
    fleet_codes = {row["qualified_code"] for row in fleet_manifest["canonical_fields"]}
    assert "hr.employee.display_name" in hr_codes
    assert "hr.employee.status" in hr_codes
    assert "fleet.vehicle.registration_plate" in fleet_codes
    assert "fleet.vehicle.vin" in fleet_codes

    assert {row["entity_type"] for row in hr_manifest["canonical_fields"]} == {ENTITY_HR_EMPLOYEE}
    assert {row["entity_type"] for row in fleet_manifest["canonical_fields"]} == {ENTITY_FLEET_VEHICLE}
    assert {row["code"] for row in hr_manifest["card_layouts"]} == {DEFAULT_HR_EMPLOYEE_LAYOUT_CODE}
    assert {row["code"] for row in fleet_manifest["card_layouts"]} == {DEFAULT_FLEET_VEHICLE_LAYOUT_CODE}


@pytest.mark.anyio
async def test_p1_platform_catalog_registers_baseline_fields(db) -> None:
    try:
        await db.execute(text("SELECT 1 FROM fr_canonical_fields LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_platform_field_registry_catalog(db)
    await db.commit()

    candidate_count = await db.scalar(
        select(func.count())
        .select_from(FrCanonicalField)
        .where(
            FrCanonicalField.tenant_id == PLATFORM_TENANT_SCOPE,
            FrCanonicalField.entity_type == ENTITY_CANDIDATE,
            FrCanonicalField.status == REGISTRY_STATUS_ACTIVE,
        )
    )
    assert candidate_count and candidate_count >= 10

    vacancy_count = await db.scalar(
        select(func.count())
        .select_from(FrCanonicalField)
        .where(
            FrCanonicalField.tenant_id == PLATFORM_TENANT_SCOPE,
            FrCanonicalField.entity_type == ENTITY_VACANCY,
        )
    )
    assert vacancy_count and vacancy_count >= 4

    client_count = await db.scalar(
        select(func.count())
        .select_from(FrCanonicalField)
        .where(
            FrCanonicalField.tenant_id == PLATFORM_TENANT_SCOPE,
            FrCanonicalField.entity_type == ENTITY_CLIENT,
        )
    )
    assert client_count and client_count >= 3

    employee_count = await db.scalar(
        select(func.count())
        .select_from(FrCanonicalField)
        .where(
            FrCanonicalField.tenant_id == PLATFORM_TENANT_SCOPE,
            FrCanonicalField.entity_type == ENTITY_HR_EMPLOYEE,
        )
    )
    assert employee_count and employee_count >= 6

    vehicle_count = await db.scalar(
        select(func.count())
        .select_from(FrCanonicalField)
        .where(
            FrCanonicalField.tenant_id == PLATFORM_TENANT_SCOPE,
            FrCanonicalField.entity_type == ENTITY_FLEET_VEHICLE,
        )
    )
    assert vehicle_count and vehicle_count >= 6


@pytest.mark.anyio
async def test_p1_tenant_seed_is_idempotent(db) -> None:
    tenant_id = f"fr-p1-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_canonical_fields LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    first = await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()
    second = await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    assert first.get("seeded") is True
    assert second.get("seeded") is False

    field_count_1 = await db.scalar(
        select(func.count()).select_from(FrCanonicalField).where(FrCanonicalField.tenant_id == tenant_id)
    )
    field_count_2 = await db.scalar(
        select(func.count()).select_from(FrCanonicalField).where(FrCanonicalField.tenant_id == tenant_id)
    )
    assert field_count_1 == field_count_2 and field_count_1 and field_count_1 > 0


@pytest.mark.anyio
async def test_p1_read_only_resolver_returns_default_candidate_layout(db) -> None:
    tenant_id = f"fr-resolver-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_CANDIDATE,
        layout_code=DEFAULT_CANDIDATE_LAYOUT_CODE,
    )
    assert layout["resolution_source"] in {"tenant_layout", "platform_layout"}
    assert layout["layout_code"] == DEFAULT_CANDIDATE_LAYOUT_CODE
    assert layout["fields"]
    assert any(f["qualified_code"] == "recruitment.candidate.first_name" for f in layout["fields"])
    assert any(f["qualified_code"] == "platform.identity.birth_date" for f in layout["fields"])


@pytest.mark.anyio
async def test_p1_list_canonical_fields_merges_platform_and_tenant(db) -> None:
    tenant_id = f"fr-list-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_canonical_fields LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    fields = await list_canonical_fields_for_scope(
        db, tenant_id=tenant_id, entity_type=ENTITY_VACANCY, module="recruitment"
    )
    codes = {row["qualified_code"] for row in fields}
    assert "recruitment.vacancy.title" in codes


@pytest.mark.anyio
async def test_p1_card_layout_profile_has_field_rows(db) -> None:
    tenant_id = f"fr-layout-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_fields LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    profile = await FieldRegistry.get_layout_profile(
        db,
        tenant_id=tenant_id,
        layout_code=DEFAULT_CLIENT_LAYOUT_CODE,
        module="crm",
    )
    assert profile is not None
    row_count = await db.scalar(
        select(func.count())
        .select_from(FrCardLayoutField)
        .where(FrCardLayoutField.layout_profile_id == profile.id)
    )
    assert row_count and row_count >= 3


@pytest.mark.anyio
async def test_p1_field_registry_read_api_fields(client, manager_headers, tenant_id) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1 FROM fr_canonical_fields LIMIT 1"))
        except Exception as exc:
            pytest.skip(f"Field Registry tables not available: {exc}")
        await ensure_tenant_field_registry_defaults(session, tenant_id)
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/field-registry/fields",
        params={"entity_type": "candidate", "module": "recruitment"},
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] >= 10
    assert any(item["qualified_code"] == "recruitment.candidate.first_name" for item in body["items"])


@pytest.mark.anyio
async def test_p1_field_registry_read_api_effective_layout(client, manager_headers, tenant_id) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1 FROM fr_canonical_fields LIMIT 1"))
        except Exception as exc:
            pytest.skip(f"Field Registry tables not available: {exc}")
        await ensure_tenant_field_registry_defaults(session, tenant_id)
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/field-registry/effective-layout",
        params={"entity_type": "vacancy", "layout_code": DEFAULT_VACANCY_LAYOUT_CODE},
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["layout_code"] == DEFAULT_VACANCY_LAYOUT_CODE
    assert body["fields"]
    assert body["sections"]
