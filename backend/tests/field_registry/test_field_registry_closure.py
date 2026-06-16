"""Field Registry Closure Gate v2 — P1–P6 foundation checks."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import func, select, text

from backend.app.field_registry.candidate_layout_bridge import (
    merge_candidate_profile_field_configs,
    resolve_effective_candidate_card_layout,
)
from backend.app.field_registry.constants import (
    DEFAULT_CANDIDATE_LAYOUT_CODE,
    DEFAULT_CLIENT_LAYOUT_CODE,
    DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
    DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
    DEFAULT_VACANCY_LAYOUT_CODE,
    ENTITY_CANDIDATE,
    ENTITY_FLEET_VEHICLE,
    ENTITY_HR_EMPLOYEE,
)
from backend.app.field_registry.intake_mapping import (
    enrich_mapping_rule_for_storage,
    legacy_normalized_target_from_qualified,
    resolve_intake_mapping_target,
)
from backend.app.field_registry.manifests.crm import crm_module_manifest
from backend.app.field_registry.manifests.fleet import fleet_module_manifest
from backend.app.field_registry.manifests.hr import hr_module_manifest
from backend.app.field_registry.manifests.recruitment import recruitment_module_manifest
from backend.app.field_registry.resolver import resolve_effective_card_layout
from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.field_registry import (
    FrCanonicalField,
    FrCardLayoutField,
    FrCardLayoutProfile,
    REGISTRY_STATUS_ACTIVE,
)
from backend.app.process_engine.manifests.recruitment import recruitment_module_manifest as pe_recruitment_manifest

_BACKEND_APP = Path(__file__).resolve().parents[2] / "app"
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[3]

_FR_MIGRATION_REVISION = "202608180001_field_registry_p1"
_FIELD_REGISTRY_SPEC = _REPO_ROOT / "docs" / "specs" / "platform" / "field-registry-card-configuration.md"

# Legacy handoff contact missing-field checks — only explicit legacy shim may retain inline phone/email/address rows.
_LEGACY_CONTACT_HANDOFF_CHECK_ALLOWLIST = {
    _BACKEND_APP / "services" / "recruitment_package_readiness.py",
}

_CLOSURE_REGRESSION_MODULES = (
    "backend/tests/field_registry/test_field_registry_p1.py",
    "backend/tests/field_registry/test_field_registry_p2.py",
    "backend/tests/field_registry/test_field_registry_p3.py",
    "backend/tests/field_registry/test_field_registry_p4.py",
    "backend/tests/field_registry/test_field_registry_p5.py",
    "backend/tests/field_registry/test_field_registry_p6.py",
    "backend/tests/services/test_transfer_policy_regression_scenarios.py",
    "hostflow-frontend/src/utils/__tests__/fieldLayoutUtils.test.ts",
)

_HANDOFF_CONTACT_MISSING_APPEND_NEEDLE = 'missing.append({"field_code":'


def _iter_app_python_files() -> list[Path]:
    files: list[Path] = []
    for path in _BACKEND_APP.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


async def _ensure_closure_tenant(db, tenant_id: str) -> None:
    await db.execute(
        sa.text(
            """
            INSERT INTO tenants (id, name, slug, api_key, is_active, type, status)
            VALUES (:id, :name, :slug, :api_key, true, 'agency', 'active')
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": tenant_id,
            "name": f"FR Closure {tenant_id}",
            "slug": f"fr-cl-{uuid.uuid4().hex[:20]}",
            "api_key": uuid.uuid4().hex[:32],
        },
    )
    await db.commit()


def test_closure_alembic_single_head() -> None:
    alembic_ini = _BACKEND_ROOT / "alembic.ini"
    if not alembic_ini.is_file():
        pytest.skip("alembic.ini not found")
    venv_alembic = _REPO_ROOT / ".venv312" / "bin" / "alembic"
    alembic_bin = str(venv_alembic) if venv_alembic.is_file() else "alembic"
    result = subprocess.run(
        [alembic_bin, "-c", str(alembic_ini), "heads"],
        cwd=str(_BACKEND_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    heads = [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith("INFO")]
    assert len(heads) == 1, f"Expected single Alembic head, got: {heads!r}"


def test_closure_fr_migration_present_in_tree() -> None:
    versions_dir = _BACKEND_ROOT / "alembic" / "versions"
    matches = list(versions_dir.glob(f"{_FR_MIGRATION_REVISION}*.py"))
    assert matches, f"Missing migration revision file for {_FR_MIGRATION_REVISION}"


def test_closure_regression_suite_modules_exist() -> None:
    for rel in _CLOSURE_REGRESSION_MODULES:
        path = _REPO_ROOT / rel
        assert path.is_file(), f"Closure regression module missing: {rel}"


def test_closure_docs_mark_p1_p6_complete() -> None:
    source = _FIELD_REGISTRY_SPEC.read_text(encoding="utf-8")
    required_markers = (
        "| **P1 — Registry schema** | **Done**",
        "| **P2 — Card UI reads layout** | **Done**",
        "| **P3 — CandidateProfile bridge** | **Done**",
        "| **P4 — Process Engine link** | **Done**",
        "| **P5 — Vacancy + intake** | **Done**",
        "| **P6 — HR / Fleet layouts** | **Done**",
        "### Closure gate v2",
    )
    for marker in required_markers:
        assert marker in source, f"Field Registry spec missing closure marker: {marker}"


def test_closure_no_hardcoded_handoff_contact_missing_checks_outside_allowlist() -> None:
    offenders: list[str] = []
    for path in _iter_app_python_files():
        if path in _LEGACY_CONTACT_HANDOFF_CHECK_ALLOWLIST:
            continue
        source = path.read_text(encoding="utf-8")
        if _HANDOFF_CONTACT_MISSING_APPEND_NEEDLE in source:
            offenders.append(str(path.relative_to(_BACKEND_APP.parent)))
    assert not offenders, (
        "Hardcoded handoff contact missing-field checks are deprecated. "
        "Use evaluate_field_requirements_for_candidate() / Field Registry qualified codes. "
        f"Offenders: {offenders}"
    )


def test_closure_transfer_policy_uses_field_requirement_evaluator() -> None:
    source = (_BACKEND_APP / "services" / "transfer_policy_resolver.py").read_text(encoding="utf-8")
    assert "evaluate_field_requirements_for_candidate" in source
    assert "field_requirements" in source


def test_closure_recruitment_package_contacts_block_uses_registry_evaluator() -> None:
    source = (_BACKEND_APP / "services" / "recruitment_package_readiness.py").read_text(encoding="utf-8")
    assert "evaluate_field_requirements_for_candidate" in source
    assert "async def _missing_contact_fields" in source
    assert "_missing_contact_fields_legacy" in source


def test_closure_pe_field_requirements_manifest_uses_qualified_codes_only() -> None:
    manifest = pe_recruitment_manifest()
    rows = manifest.get("field_requirements") or []
    assert rows, "Expected recruitment PE field_requirements seed rows"
    for requirement in rows:
        config = dict(requirement.get("config") or {})
        for field_spec in config.get("fields") or []:
            qualified = str(field_spec.get("qualified_code") or "").strip()
            assert qualified, f"Field requirement must use qualified_code, got: {field_spec!r}"
            assert "." in qualified, f"qualified_code must be namespaced, got: {qualified!r}"
            legacy_only = str(field_spec.get("field_code") or "").strip()
            assert not legacy_only or qualified, (
                "Legacy field_code without qualified_code is not allowed in PE manifest"
            )


def test_closure_intake_mapping_uses_canonical_qualified_codes_with_legacy_compatibility() -> None:
    qualified_rule = enrich_mapping_rule_for_storage(
        {
            "source": "phone_number",
            "qualified_field_code": "recruitment.candidate.contacts.phone",
            "format": "phone",
        }
    )
    assert qualified_rule["qualified_field_code"] == "recruitment.candidate.contacts.phone"
    assert qualified_rule["target"] == "phone"
    assert resolve_intake_mapping_target(qualified_rule) == "phone"

    legacy_rule = enrich_mapping_rule_for_storage({"source": "email", "target": "email"})
    assert legacy_rule["qualified_field_code"] == "recruitment.candidate.contacts.email"
    assert resolve_intake_mapping_target(legacy_rule) == "email"
    assert legacy_normalized_target_from_qualified("platform.identity.address") == "address"


def test_closure_candidate_profile_bridge_empty_config_preserves_registry_layout() -> None:
    layout = {
        "entity_type": "candidate",
        "resolution_source": "platform_layout",
        "sections": [{"code": "basic", "order": 10, "fields": []}],
        "fields": [
            {
                "qualified_code": "recruitment.candidate.first_name",
                "legacy_aliases": ["first_name"],
                "visible": True,
                "required": True,
                "section_code": "basic",
                "sort_order": 10,
            }
        ],
    }
    profile = CandidateProfile(
        id="profile-empty",
        tenant_id="tenant-1",
        code="driver_ce_default",
        name="Default",
        config={"field_configs": []},
    )
    merged = merge_candidate_profile_field_configs(layout, profile)
    assert merged == layout


@pytest.mark.anyio
async def test_closure_seed_idempotent_registry_counts(db) -> None:
    tenant_id = f"fr-closure-idem-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_canonical_fields LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await _ensure_closure_tenant(db, tenant_id)
    expected_layouts = sum(
        len(manifest.get("card_layouts") or [])
        for manifest in (
            recruitment_module_manifest(),
            crm_module_manifest(),
            hr_module_manifest(),
            fleet_module_manifest(),
        )
    )

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    field_count_1 = await db.scalar(
        select(func.count()).select_from(FrCanonicalField).where(FrCanonicalField.tenant_id == tenant_id)
    )
    layout_count_1 = await db.scalar(
        select(func.count()).select_from(FrCardLayoutProfile).where(FrCardLayoutProfile.tenant_id == tenant_id)
    )
    layout_field_count_1 = await db.scalar(
        select(func.count())
        .select_from(FrCardLayoutField)
        .join(FrCardLayoutProfile, FrCardLayoutProfile.id == FrCardLayoutField.layout_profile_id)
        .where(FrCardLayoutProfile.tenant_id == tenant_id)
    )

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()

    field_count_2 = await db.scalar(
        select(func.count()).select_from(FrCanonicalField).where(FrCanonicalField.tenant_id == tenant_id)
    )
    layout_count_2 = await db.scalar(
        select(func.count()).select_from(FrCardLayoutProfile).where(FrCardLayoutProfile.tenant_id == tenant_id)
    )
    layout_field_count_2 = await db.scalar(
        select(func.count())
        .select_from(FrCardLayoutField)
        .join(FrCardLayoutProfile, FrCardLayoutProfile.id == FrCardLayoutField.layout_profile_id)
        .where(FrCardLayoutProfile.tenant_id == tenant_id)
    )

    assert field_count_1 == field_count_2 and field_count_1 and field_count_1 > 0
    assert layout_count_1 == layout_count_2 == expected_layouts
    assert layout_field_count_1 == layout_field_count_2 and layout_field_count_1 and layout_field_count_1 > 0


@pytest.mark.anyio
async def test_closure_existing_tenant_upgrade_receives_baseline_artifacts(db) -> None:
    tenant_id = f"fr-closure-upg-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await _ensure_closure_tenant(db, tenant_id)
    seeded = await ensure_tenant_field_registry_defaults(db, tenant_id)
    await db.commit()
    assert seeded.get("seeded") is True

    candidate_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_CANDIDATE,
        layout_code=DEFAULT_CANDIDATE_LAYOUT_CODE,
    )
    assert candidate_layout["resolution_source"] != "not_found"
    assert candidate_layout["layout_code"] == DEFAULT_CANDIDATE_LAYOUT_CODE
    assert any(
        row["qualified_code"] == "recruitment.candidate.first_name" for row in candidate_layout["fields"]
    )

    vacancy_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type="vacancy",
        layout_code=DEFAULT_VACANCY_LAYOUT_CODE,
        module="recruitment",
    )
    assert vacancy_layout["resolution_source"] != "not_found"
    assert vacancy_layout["layout_code"] == DEFAULT_VACANCY_LAYOUT_CODE
    assert any(row["qualified_code"] == "recruitment.vacancy.title" for row in vacancy_layout["fields"])

    client_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type="client",
        layout_code=DEFAULT_CLIENT_LAYOUT_CODE,
        module="crm",
    )
    assert client_layout["resolution_source"] != "not_found"
    assert client_layout["layout_code"] == DEFAULT_CLIENT_LAYOUT_CODE
    assert any(row["qualified_code"] == "crm.client.name" for row in client_layout["fields"])

    hr_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_HR_EMPLOYEE,
        layout_code=DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
        module="hr",
    )
    assert hr_layout["resolution_source"] != "not_found"
    assert hr_layout["layout_code"] == DEFAULT_HR_EMPLOYEE_LAYOUT_CODE
    assert any(row["qualified_code"] == "hr.employee.display_name" for row in hr_layout["fields"])

    fleet_layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_id,
        entity_type=ENTITY_FLEET_VEHICLE,
        layout_code=DEFAULT_FLEET_VEHICLE_LAYOUT_CODE,
        module="fleet",
    )
    assert fleet_layout["resolution_source"] != "not_found"
    assert fleet_layout["layout_code"] == DEFAULT_FLEET_VEHICLE_LAYOUT_CODE
    assert any(row["qualified_code"] == "fleet.vehicle.registration_plate" for row in fleet_layout["fields"])

    active_field_count = await db.scalar(
        select(func.count())
        .select_from(FrCanonicalField)
        .where(
            FrCanonicalField.tenant_id == tenant_id,
            FrCanonicalField.status == REGISTRY_STATUS_ACTIVE,
        )
    )
    assert active_field_count and active_field_count >= 10


@pytest.mark.anyio
async def test_closure_candidate_profile_bridge_overlay_on_upgrade_tenant(db) -> None:
    tenant_id = f"fr-closure-bridge-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM fr_card_layout_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Field Registry tables not available: {exc}")

    await _ensure_closure_tenant(db, tenant_id)
    await ensure_tenant_field_registry_defaults(db, tenant_id)

    profile = CandidateProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=f"closure_profile_{uuid.uuid4().hex[:6]}",
        name="Closure overlay profile",
        config={
            "field_configs": [
                {
                    "field_key": "email",
                    "field_type": "email",
                    "visible": False,
                    "required": True,
                    "order": 1,
                    "label": "Registry overlay email",
                }
            ]
        },
    )
    db.add(profile)
    await db.commit()

    layout = await resolve_effective_candidate_card_layout(
        db,
        tenant_id=tenant_id,
        candidate_profile_id=profile.id,
        layout_code=DEFAULT_CANDIDATE_LAYOUT_CODE,
    )
    email = next(
        (row for row in layout["fields"] if row["qualified_code"] == "recruitment.candidate.contacts.email"),
        None,
    )
    assert email is not None
    assert email["visible"] is False
    assert email["required"] is True
    assert email.get("label_override") == "Registry overlay email"
    assert layout.get("candidate_profile_id") == profile.id
