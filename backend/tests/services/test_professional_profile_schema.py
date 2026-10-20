"""Schema step evidence for the professional profile domain.

The resolver is not part of this slice. These checks lock the schema,
the timezone rule, and the legacy writer inventory.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.tenant import Tenant
from backend.app.reference.professional_profile_catalogs import catalog_code_pairs
from backend.app.services.professional_profile_legacy_writers import (
    LEGACY_WRITERS,
    ObservedWrite,
    classify_writes,
)
from backend.app.services.workspace_timezone import WorkspaceTimezoneError, require_iana_timezone


def test_timezone_requires_an_explicit_iana_zone() -> None:
    assert require_iana_timezone("Europe/Madrid") == "Europe/Madrid"
    assert require_iana_timezone(" UTC ") == "UTC"
    with pytest.raises(WorkspaceTimezoneError) as missing:
        require_iana_timezone("  ")
    assert missing.value.code == "workspace_timezone_required"
    with pytest.raises(WorkspaceTimezoneError) as invalid:
        require_iana_timezone("Not/AZone")
    assert invalid.value.code == "workspace_timezone_invalid"


def test_tenant_timezone_column_has_no_default() -> None:
    column = Tenant.__table__.c.timezone
    assert column.nullable is False
    assert column.default is None
    assert column.server_default is None


def test_employment_facet_columns_exist_on_the_model() -> None:
    columns = CandidateEmployment.__table__.c
    for name in (
        "driving_categories",
        "operation_scopes",
        "movement_patterns",
        "crew_modes",
        "work_areas",
    ):
        assert name in columns
        assert columns[name].nullable is False


def test_legacy_writer_inventory_is_complete_and_still_required() -> None:
    unclassified, missing, removable = classify_writes()
    assert unclassified == []
    assert missing == []
    assert removable == []
    for writer in LEGACY_WRITERS:
        assert writer.owner
        assert writer.semantic_intent
        assert writer.source_value
        assert writer.target_legacy_field
        assert writer.compatibility_reason
        assert writer.retirement_condition
        assert writer.retirement_status == "still_required"


def test_unclassified_legacy_writer_fails() -> None:
    unclassified, _, _ = classify_writes(
        [
            ObservedWrite(
                "backend/app/new_legacy_writer.py",
                "experience_eu_years",
                'extra["experience_eu_years"] = 3',
            )
        ]
    )
    assert len(unclassified) == 1
    assert unclassified[0].path == "backend/app/new_legacy_writer.py"


def test_ce_bridge_writer_becomes_removable_when_its_condition_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.services.professional_profile_legacy_writers as writers

    monkeypatch.setattr(writers, "DECLARED_CE_FROM_RESOLVER", True)
    monkeypatch.setattr(writers, "CANDIDATE_PROFILE_ON_RESOLVER", True)
    monkeypatch.setattr(writers, "CE_CONSUMERS_MIGRATED", True)
    monkeypatch.setattr(writers, "EU_CONSUMERS_MIGRATED", True)
    bridge = next(
        writer
        for writer in writers.LEGACY_WRITERS
        if writer.owner == "backend/app/api/public/intake.py"
        and writer.target_legacy_field == "experience_eu_years"
    )
    assert bridge.retirement_status == "removable"
    _, _, removable = writers.classify_writes()
    assert bridge in removable


@pytest.mark.anyio
async def test_database_schema_and_timezone_backfill() -> None:
    from backend.app.api.v1.tenants.service import create_tenant
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        column = (
            await session.execute(
                text(
                    """
                    SELECT column_default, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'tenants'
                      AND column_name = 'timezone'
                    """
                )
            )
        ).one()
        assert column.column_default is None
        assert column.is_nullable == "NO"
        nulls = await session.scalar(text("SELECT count(*) FROM tenants WHERE timezone IS NULL"))
        assert nulls == 0

        codes = (
            await session.execute(
                text(
                    """
                    SELECT vocabulary, code
                    FROM professional_catalog_codes
                    ORDER BY vocabulary, code
                    """
                )
            )
        ).all()
        assert [(row.vocabulary, row.code) for row in codes] == sorted(catalog_code_pairs())
        mappings = await session.scalar(text("SELECT count(*) FROM professional_code_mappings"))
        assert mappings == 0

        employment_columns = (
            await session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'candidate_employments'
                      AND column_name IN (
                        'driving_categories',
                        'operation_scopes',
                        'movement_patterns',
                        'crew_modes',
                        'work_areas'
                      )
                    """
                )
            )
        ).scalars().all()
        assert set(employment_columns) == {
            "driving_categories",
            "operation_scopes",
            "movement_patterns",
            "crew_modes",
            "work_areas",
        }

        policies = (
            await session.execute(
                text(
                    """
                    SELECT tablename
                    FROM pg_policies
                    WHERE policyname LIKE 'rls_%_tenant'
                      AND tablename IN (
                        'candidate_professional_constraints',
                        'candidate_availability',
                        'candidate_preference_choices',
                        'candidate_compensation_expectations',
                        'professional_catalog_codes',
                        'professional_code_mappings'
                      )
                    """
                )
            )
        ).scalars().all()
        assert set(policies) == {
            "candidate_professional_constraints",
            "candidate_availability",
            "candidate_preference_choices",
            "candidate_compensation_expectations",
        }

        slug = f"tz-madrid-{uuid.uuid4().hex[:8]}"
        tenant = await create_tenant(
            session,
            {
                "name": f"Madrid {slug}",
                "slug": slug,
                "timezone": "Europe/Madrid",
            },
        )
        try:
            assert tenant.timezone == "Europe/Madrid"
        finally:
            await session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant.id})
            await session.commit()

        with pytest.raises(ValueError, match="workspace_timezone_required"):
            await create_tenant(
                session,
                {
                    "name": f"Missing {slug}",
                    "slug": f"{slug}-missing",
                    "timezone": "",
                },
            )
