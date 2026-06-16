"""Process Engine closure gate — P0–P6 stabilization checks."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import func, select, text

from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.process_engine import (
    PeHandoffRule,
    PeProcessProfile,
    PeTransitionRule,
    REGISTRY_STATUS_ACTIVE,
)
from backend.app.process_engine.manifests.recruitment import (
    DEFAULT_PROFILE_CODE,
    RECRUITMENT_MODULE,
    RECRUITMENT_PIPELINE_GATES_RULE_CODE,
    recruitment_module_manifest,
)
from backend.app.process_engine.seed import ensure_recruitment_process_engine_defaults
from backend.app.process_engine.transition_rules_adapter import (
    gates_from_transition_rule_config,
    load_hiring_pipeline_gates_rule,
)
from backend.app.services.hiring_pipeline_gates import patch_settings_dict

_BACKEND_APP = Path(__file__).resolve().parents[2] / "app"
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Legacy tenant blob readers/writers — only these modules may touch hiring_stage_gates_v1 directly.
_LEGACY_TENANT_GATES_ALLOWLIST = {
    _BACKEND_APP / "services" / "hiring_pipeline_gates.py",
    _BACKEND_APP / "process_engine" / "transition_rules_adapter.py",
    _BACKEND_APP / "api" / "v1" / "settings" / "hiring_pipeline_gates_impl.py",
}

_PE_MIGRATION_REVISIONS = (
    "202608140001_process_engine_registry_p1",
    "202608160001_vacancy_process_profile_binding_p3",
)

_CLOSURE_REGRESSION_MODULES = (
    "backend/tests/process_engine/test_process_engine_p6.py",
    "backend/tests/services/test_transfer_policy_regression_scenarios.py",
    "backend/tests/api/test_transfer_policy_regression.py",
    "backend/tests/api/test_recruitment_lock_bulk_guard.py",
    "backend/tests/test_hiring_pipeline_gates.py",
)


def _iter_app_python_files() -> list[Path]:
    files: list[Path] = []
    for path in _BACKEND_APP.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


async def _ensure_closure_tenant(db, tenant_id: str) -> str:
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
            "name": f"PE Closure {tenant_id}",
            "slug": f"pe-cl-{uuid.uuid4().hex[:20]}",
            "api_key": uuid.uuid4().hex[:32],
        },
    )
    funnel_id = str(uuid.uuid4())
    await db.execute(
        sa.text(
            """
            INSERT INTO funnels (id, tenant_id, type, name, is_default)
            VALUES (:id, :tenant_id, 'candidate', 'Default Candidate Funnel', true)
            """
        ),
        {"id": funnel_id, "tenant_id": tenant_id},
    )
    for code, label, order in (
        ("new", "New", 10),
        ("contacted", "Contacted", 20),
        ("docs_wait", "Waiting for documents", 30),
        ("docs_got", "Documents received", 40),
        ("ready_for_handoff", "Ready for handoff", 50),
        ("rejected", "Rejected", 60),
    ):
        await db.execute(
            sa.text(
                """
                INSERT INTO funnel_stages (id, funnel_id, code, label, system_stage, "order", is_terminal)
                VALUES (:id, :funnel_id, :code, :label, 'in_progress', :ord, false)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "funnel_id": funnel_id,
                "code": code,
                "label": label,
                "ord": order,
            },
        )
    await db.commit()
    return funnel_id


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


def test_closure_pe_migrations_present_in_tree() -> None:
    versions_dir = _BACKEND_ROOT / "alembic" / "versions"
    for revision in _PE_MIGRATION_REVISIONS:
        matches = list(versions_dir.glob(f"{revision}*.py"))
        assert matches, f"Missing migration revision file for {revision}"


def test_closure_no_direct_hiring_gates_from_tenant_settings_outside_allowlist() -> None:
    offenders: list[str] = []
    for path in _iter_app_python_files():
        if path in _LEGACY_TENANT_GATES_ALLOWLIST:
            continue
        source = path.read_text(encoding="utf-8")
        if "hiring_gates_from_tenant_settings" in source:
            offenders.append(str(path.relative_to(_BACKEND_APP.parent)))
    assert not offenders, (
        "Direct hiring_gates_from_tenant_settings() is deprecated for runtime. "
        "Use resolve_hiring_pipeline_gates(db, tenant_id, candidate_id=…). "
        f"Offenders: {offenders}"
    )


def test_closure_no_direct_hiring_stage_gates_v1_blob_access_outside_allowlist() -> None:
    offenders: list[str] = []
    needle = "hiring_stage_gates_v1"
    for path in _iter_app_python_files():
        if path in _LEGACY_TENANT_GATES_ALLOWLIST:
            continue
        source = path.read_text(encoding="utf-8")
        if needle in source:
            rel = str(path.relative_to(_BACKEND_APP.parent))
            # transfer_policy_resolver documents legacy storage in policy metadata only.
            if rel.endswith("services/transfer_policy_resolver.py"):
                continue
            offenders.append(rel)
    assert not offenders, (
        "Direct tenant.settings['hiring_stage_gates_v1'] access is deprecated. "
        "Route through pe_transition_rules via resolve_hiring_pipeline_gates(). "
        f"Offenders: {offenders}"
    )


def test_closure_runtime_paths_use_resolve_hiring_pipeline_gates() -> None:
    required_paths = (
        _BACKEND_APP / "api" / "v1" / "candidates" / "service.py",
        _BACKEND_APP / "services" / "candidate_doc_pipeline_guard.py",
        _BACKEND_APP / "services" / "transfer_policy_resolver.py",
        _BACKEND_APP / "api" / "v1" / "candidates" / "pipeline_overrides_service.py",
    )
    for path in required_paths:
        source = path.read_text(encoding="utf-8")
        assert "resolve_hiring_pipeline_gates" in source, (
            f"{path.relative_to(_BACKEND_APP.parent)} must resolve gates via Process Engine adapter path"
        )


def test_closure_regression_suite_modules_exist() -> None:
    for rel in _CLOSURE_REGRESSION_MODULES:
        path = _REPO_ROOT / rel
        assert path.is_file(), f"Closure regression module missing: {rel}"


@pytest.mark.anyio
async def test_closure_seed_idempotent_registry_counts(db) -> None:
    tenant_id = f"pe-closure-idem-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM pe_system_stages LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Process Engine tables not available: {exc}")

    await _ensure_closure_tenant(db, tenant_id)
    manifest = recruitment_module_manifest()

    await ensure_recruitment_process_engine_defaults(db, tenant_id)
    await db.commit()

    stage_count_1 = await db.scalar(
        select(func.count()).select_from(PeHandoffRule).where(
            PeHandoffRule.tenant_id == tenant_id,
            PeHandoffRule.module == RECRUITMENT_MODULE,
        )
    )
    transition_count_1 = await db.scalar(
        select(func.count()).select_from(PeTransitionRule).where(
            PeTransitionRule.tenant_id == tenant_id,
            PeTransitionRule.module == RECRUITMENT_MODULE,
        )
    )

    await ensure_recruitment_process_engine_defaults(db, tenant_id)
    await db.commit()

    stage_count_2 = await db.scalar(
        select(func.count()).select_from(PeHandoffRule).where(
            PeHandoffRule.tenant_id == tenant_id,
            PeHandoffRule.module == RECRUITMENT_MODULE,
        )
    )
    transition_count_2 = await db.scalar(
        select(func.count()).select_from(PeTransitionRule).where(
            PeTransitionRule.tenant_id == tenant_id,
            PeTransitionRule.module == RECRUITMENT_MODULE,
        )
    )

    assert stage_count_1 == stage_count_2 == len(manifest["handoff_rules"])
    assert transition_count_1 == transition_count_2 == len(manifest["transition_rules"])


@pytest.mark.anyio
async def test_closure_existing_tenant_upgrade_receives_pe_artifacts(db) -> None:
    tenant_id = f"pe-closure-upg-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM pe_process_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Process Engine tables not available: {exc}")

    await _ensure_closure_tenant(db, tenant_id)

    custom_settings = patch_settings_dict(
        {},
        {"contact_attempt_gate_stages": ["contacted", "questionnaire_submitted"]},
    )
    await db.execute(
        sa.text("UPDATE tenants SET settings = CAST(:settings AS jsonb) WHERE id = :tenant_id"),
        {"tenant_id": tenant_id, "settings": json.dumps(custom_settings)},
    )
    await db.commit()

    await ensure_recruitment_process_engine_defaults(db, tenant_id)
    await db.commit()

    profile = await db.scalar(
        select(PeProcessProfile).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.module == RECRUITMENT_MODULE,
            PeProcessProfile.code == DEFAULT_PROFILE_CODE,
            PeProcessProfile.status == REGISTRY_STATUS_ACTIVE,
        )
    )
    assert profile is not None
    assert profile.is_default is True

    handoff_count = await db.scalar(
        select(func.count()).select_from(PeHandoffRule).where(
            PeHandoffRule.tenant_id == tenant_id,
            PeHandoffRule.module == RECRUITMENT_MODULE,
            PeHandoffRule.status == REGISTRY_STATUS_ACTIVE,
        )
    )
    assert handoff_count == len(recruitment_module_manifest()["handoff_rules"])

    gates_rule = await load_hiring_pipeline_gates_rule(
        db,
        tenant_id=tenant_id,
        process_profile_id=str(profile.id),
    )
    assert gates_rule is not None
    assert gates_rule.code == RECRUITMENT_PIPELINE_GATES_RULE_CODE
    migrated_gates = gates_from_transition_rule_config(dict(gates_rule.config or {}))
    assert migrated_gates is not None
    assert migrated_gates.contact_attempt_gate_stages == frozenset(
        {"contacted", "questionnaire_submitted"}
    )

    funnel = await db.scalar(
        select(Funnel).where(
            Funnel.tenant_id == tenant_id,
            Funnel.type == "candidate",
            Funnel.is_default.is_(True),
        )
    )
    assert funnel is not None
    mapped_stage_count = await db.scalar(
        select(func.count()).select_from(FunnelStage).where(
            FunnelStage.funnel_id == funnel.id,
            FunnelStage.pe_maps_to_code.is_not(None),
            FunnelStage.pe_maps_to_module == RECRUITMENT_MODULE,
        )
    )
    assert mapped_stage_count and mapped_stage_count >= 5
