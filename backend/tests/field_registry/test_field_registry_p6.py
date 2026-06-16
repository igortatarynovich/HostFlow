"""Field Registry P6 — HR / Fleet baseline card layouts."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text

from backend.app.field_registry.constants import (
    DEFAULT_CLIENT_LAYOUT_CODE,
    DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
    DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
    DEFAULT_VACANCY_LAYOUT_CODE,
    ENTITY_FLEET_VEHICLE,
    ENTITY_HR_EMPLOYEE,
    FLEET_MODULE,
    HR_MODULE,
)
from backend.app.field_registry.resolver import resolve_effective_card_layout
from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
from backend.app.models.field_registry import FrCanonicalField, FrCardLayoutField, FrCardLayoutProfile


@pytest.mark.anyio
async def test_p6_seed_adds_hr_and_fleet_baseline_fields(db) -> None:
    tenant_id = f"fr-p6-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_canonical_fields LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    first = await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()
    second = await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    assert first["seeded"] is True
    assert second["seeded"] is False
    assert first["hr_fields"] >= 6
    assert first["fleet_fields"] >= 6

    hr_codes = set(
        (
            await db.execute(
                select(FrCanonicalField.qualified_code).where(
                    FrCanonicalField.tenant_id == tenant_id,
                    FrCanonicalField.module == HR_MODULE,
                    FrCanonicalField.entity_type == ENTITY_HR_EMPLOYEE,
                )
            )
        )
        .scalars()
        .all()
    )
    fleet_codes = set(
        (
            await db.execute(
                select(FrCanonicalField.qualified_code).where(
                    FrCanonicalField.tenant_id == tenant_id,
                    FrCanonicalField.module == FLEET_MODULE,
                    FrCanonicalField.entity_type == ENTITY_FLEET_VEHICLE,
                )
            )
        )
        .scalars()
        .all()
    )
    assert {"hr.employee.display_name", "hr.employee.status", "hr.employee.hire_date"}.issubset(hr_codes)
    assert {"fleet.vehicle.registration_plate", "fleet.vehicle.vin", "fleet.vehicle.status"}.issubset(
        fleet_codes
    )


@pytest.mark.anyio
async def test_p6_effective_layout_returns_hr_and_fleet_layouts(db) -> None:
    tenant_id = f"fr-p6-layout-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    hr_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_HR_EMPLOYEE,
        layout_code=DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
        module=HR_MODULE,
    )
    assert hr_layout["resolution_source"] != "not_found"
    assert hr_layout["layout_code"] == DEFAULT_HR_EMPLOYEE_LAYOUT_CODE
    assert {row["qualified_code"] for row in hr_layout["fields"]} >= {
        "hr.employee.display_name",
        "hr.employee.status",
    }

    fleet_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_FLEET_VEHICLE,
        layout_code=DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
        module=FLEET_MODULE,
    )
    assert fleet_layout["resolution_source"] != "not_found"
    assert fleet_layout["layout_code"] == DEFAULT_FLEET_VEHICLE_LAYOUT_CODE
    assert {row["qualified_code"] for row in fleet_layout["fields"]} >= {
        "fleet.vehicle.registration_plate",
        "fleet.vehicle.vin",
    }


@pytest.mark.anyio
async def test_p6_existing_tenant_upgrade_receives_hr_fleet_without_breaking_existing_layouts(db) -> None:
    tenant_id = f"fr-p6-upg-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.flush()
    await db.execute(
        text(
            """
            DELETE FROM fr_card_layout_fields
            WHERE layout_profile_id IN (
                SELECT id FROM fr_card_layout_profiles
                WHERE tenant_id = :tenant_id AND module IN ('hr', 'fleet')
            )
            """
        ),
        {"tenant_id": tenant_id},
    )
    await db.execute(
        text("DELETE FROM fr_card_layout_profiles WHERE tenant_id = :tenant_id AND module IN ('hr', 'fleet')"),
        {"tenant_id": tenant_id},
    )
    await db.execute(
        text("DELETE FROM fr_canonical_fields WHERE tenant_id = :tenant_id AND module IN ('hr', 'fleet')"),
        {"tenant_id": tenant_id},
    )
    await db.commit()

    upgraded = await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()
    assert upgraded["seeded"] is True

    expected_layouts = {
        DEFAULT_VACANCY_LAYOUT_CODE,
        DEFAULT_CLIENT_LAYOUT_CODE,
        DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
        DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
    }
    layout_codes = set(
        (
            await db.execute(
                select(FrCardLayoutProfile.code).where(
                    FrCardLayoutProfile.tenant_id == tenant_id,
                    FrCardLayoutProfile.code.in_(expected_layouts),
                )
            )
        )
        .scalars()
        .all()
    )
    assert expected_layouts.issubset(layout_codes)

    layout_field_count = await db.scalar(
        select(func.count())
        .select_from(FrCardLayoutField)
        .join(FrCardLayoutProfile, FrCardLayoutProfile.id == FrCardLayoutField.layout_profile_id)
        .where(
            FrCardLayoutProfile.tenant_id == tenant_id,
            FrCardLayoutProfile.code.in_(
                {DEFAULT_HR_EMPLOYEE_LAYOUT_CODE, DEFAULT_FLEET_VEHICLE_LAYOUT_CODE}
            ),
        )
    )
    assert layout_field_count and layout_field_count >= 12
