"""Module Registry P1 — schema, seed baseline, resolver, read API."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy import func, select, text

from backend.app.auth.deps import Role, UserCtx
from backend.app.auth.fleet_access import require_fleet_module_access
from backend.app.auth.hr_workforce_access import require_hr_workforce_module_access
from backend.app.models.module_registry import (
    INSTALLATION_STATE_ENABLED,
    INSTALLATION_STATE_SUSPENDED,
    INSTALLATION_STATE_UNINSTALLED,
    ModuleCapability,
    ModuleDependency,
    ModuleRegistry,
    TenantModuleInstallation,
)
from backend.app.module_registry.manifest import BASELINE_MODULE_CODES, module_registry_manifest
from backend.app.module_registry.resolver import is_module_installed, list_installed_modules
from backend.app.module_registry.seed import ensure_module_registry_baseline, ensure_tenant_module_installations
from backend.app.process_engine.handoff_evaluator import get_installed_modules


async def _ensure_tenant(db, tenant_id: str, *, modules: dict[str, bool] | None = None) -> None:
    await db.execute(
        sa.text(
            """
            INSERT INTO tenants (id, name, slug, api_key, is_active, type, status, settings)
            VALUES (:id, :name, :slug, :api_key, true, 'agency', 'active', CAST(:settings AS jsonb))
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": tenant_id,
            "name": f"MR P1 {tenant_id}",
            "slug": f"mr-p1-{uuid.uuid4().hex[:20]}",
            "api_key": uuid.uuid4().hex[:32],
            "settings": json.dumps({"modules": modules or {}}),
        },
    )
    await db.commit()


def _ctx(tenant_id: str, role: str = Role.administrator.value) -> UserCtx:
    return UserCtx(
        sub="module-registry-p2",
        email="module-registry-p2@example.test",
        role=role,
        tenant_id=tenant_id,
        supervisor_id=None,
        raw={},
    )


async def _set_installation_state(db, tenant_id: str, module_code: str, state: str) -> None:
    row = (
        await db.execute(
            select(TenantModuleInstallation).where(
                TenantModuleInstallation.tenant_id == tenant_id,
                TenantModuleInstallation.module_code == module_code,
            )
        )
    ).scalar_one()
    row.state = state
    await db.commit()


def test_p1_module_registry_manifest_declares_baseline_modules() -> None:
    rows = module_registry_manifest()
    codes = {row["module_code"] for row in rows}
    assert set(BASELINE_MODULE_CODES).issubset(codes)
    recruitment = next(row for row in rows if row["module_code"] == "recruitment")
    assert any(cap["capability_code"] == "recruitment.candidate.view" for cap in recruitment["capabilities"])
    assert any(dep["dependency_module_code"] == "hr" for dep in recruitment["dependencies"])


@pytest.mark.anyio
async def test_p1_seed_baseline_is_idempotent(db) -> None:
    tenant_id = f"mr-p1-idem-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM module_registry LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Module Registry tables not available: {exc}")

    await _ensure_tenant(db, tenant_id)
    first = await ensure_tenant_module_installations(db, tenant_id)
    await db.commit()
    second = await ensure_tenant_module_installations(db, tenant_id)
    await db.commit()

    assert first["seeded"] is True
    assert second["seeded"] is False

    module_count = await db.scalar(select(func.count()).select_from(ModuleRegistry))
    install_count = await db.scalar(
        select(func.count()).select_from(TenantModuleInstallation).where(TenantModuleInstallation.tenant_id == tenant_id)
    )
    capability_count = await db.scalar(select(func.count()).select_from(ModuleCapability))
    dependency_count = await db.scalar(select(func.count()).select_from(ModuleDependency))

    assert module_count and module_count >= len(BASELINE_MODULE_CODES)
    assert install_count == len(BASELINE_MODULE_CODES)
    assert capability_count and capability_count >= 6
    assert dependency_count and dependency_count >= 1


@pytest.mark.anyio
async def test_p1_seed_reflects_legacy_lifecycle_states(db) -> None:
    tenant_id = f"mr-p1-state-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM tenant_module_installations LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Module Registry tables not available: {exc}")

    await _ensure_tenant(db, tenant_id, modules={"hr": False, "fleet": True})
    await ensure_tenant_module_installations(db, tenant_id)
    await db.commit()

    rows = {
        row.module_code: row
        for row in (
            await db.execute(
                select(TenantModuleInstallation).where(TenantModuleInstallation.tenant_id == tenant_id)
            )
        ).scalars()
    }
    assert rows["hr"].state == INSTALLATION_STATE_SUSPENDED
    assert rows["fleet"].state == INSTALLATION_STATE_ENABLED
    assert rows["process_engine"].state == INSTALLATION_STATE_ENABLED

    rows["fleet"].state = INSTALLATION_STATE_UNINSTALLED
    await db.commit()
    await ensure_tenant_module_installations(db, tenant_id)
    await db.commit()
    assert await is_module_installed(db, tenant_id, "fleet") is False


@pytest.mark.anyio
async def test_p1_resolver_and_capability_read(db) -> None:
    tenant_id = f"mr-p1-resolve-{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(text("SELECT 1 FROM module_capabilities LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Module Registry tables not available: {exc}")

    await _ensure_tenant(db, tenant_id, modules={"hr": True})
    await ensure_tenant_module_installations(db, tenant_id)
    await db.commit()

    assert await is_module_installed(db, tenant_id, "hr") is True
    assert await is_module_installed(db, tenant_id, "unknown") is False

    modules = await list_installed_modules(db, tenant_id=tenant_id)
    by_code = {row["module_code"]: row for row in modules}
    assert "hr" in by_code
    assert any(cap["capability_code"] == "hr.workspace.view" for cap in by_code["hr"]["capabilities"])
    assert any(dep["dependency_module_code"] == "hr" for dep in by_code["recruitment"]["dependencies"])


@pytest.mark.anyio
async def test_p1_read_api_returns_installed_modules_and_capabilities(client, manager_headers, tenant_id) -> None:
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1 FROM module_registry LIMIT 1"))
        except Exception as exc:
            pytest.skip(f"Module Registry tables not available: {exc}")
        await ensure_module_registry_baseline(session)
        await ensure_tenant_module_installations(session, tenant_id)
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/module-registry/installed-modules",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] >= len(BASELINE_MODULE_CODES)
    modules = {row["module_code"]: row for row in body["items"]}
    assert "recruitment" in modules
    assert "field_registry" in modules
    assert any(
        cap["capability_code"] == "recruitment.candidate.view"
        for cap in modules["recruitment"]["capabilities"]
    )

    installed = await client.get(
        "/api/v1/platform/module-registry/installed-modules/hr/installed",
        headers=manager_headers,
    )
    assert installed.status_code == 200, installed.text
    assert installed.json()["module_code"] == "hr"


@pytest.mark.anyio
async def test_p2_process_engine_installed_modules_use_module_registry_first(db) -> None:
    tenant_id = str(uuid.uuid4())
    try:
        await db.execute(text("SELECT 1 FROM tenant_module_installations LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Module Registry tables not available: {exc}")

    await _ensure_tenant(db, tenant_id, modules={"hr": True})
    await ensure_tenant_module_installations(db, tenant_id)
    await db.commit()

    assert "hr" in await get_installed_modules(db, tenant_id)

    await _set_installation_state(db, tenant_id, "hr", INSTALLATION_STATE_SUSPENDED)
    installed = await get_installed_modules(db, tenant_id)
    assert "recruitment" in installed
    assert "hr" not in installed


@pytest.mark.anyio
async def test_p2_hr_and_fleet_guards_use_module_registry_state(db) -> None:
    tenant_id = str(uuid.uuid4())
    try:
        await db.execute(text("SELECT 1 FROM tenant_module_installations LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Module Registry tables not available: {exc}")

    await _ensure_tenant(db, tenant_id, modules={"hr": True, "fleet": True})
    await ensure_tenant_module_installations(db, tenant_id)
    await db.commit()

    ctx = _ctx(tenant_id)
    assert await require_hr_workforce_module_access(ctx, (db, uuid.UUID(tenant_id))) is ctx
    assert await require_fleet_module_access(ctx, (db, uuid.UUID(tenant_id))) is ctx

    await _set_installation_state(db, tenant_id, "hr", INSTALLATION_STATE_SUSPENDED)
    await _set_installation_state(db, tenant_id, "fleet", INSTALLATION_STATE_SUSPENDED)

    with pytest.raises(HTTPException) as hr_exc:
        await require_hr_workforce_module_access(ctx, (db, uuid.UUID(tenant_id)))
    assert hr_exc.value.status_code == 403

    with pytest.raises(HTTPException) as fleet_exc:
        await require_fleet_module_access(ctx, (db, uuid.UUID(tenant_id)))
    assert fleet_exc.value.status_code == 403


def test_p2_no_new_direct_legacy_module_flag_reads() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    app_root = repo_root / "backend" / "app"
    allowed = {
        app_root / "api" / "v1" / "platform" / "tenants.py",
        app_root / "api" / "v1" / "settings" / "team.py",
        app_root / "api" / "v1" / "tenants" / "service.py",
        app_root / "module_registry" / "resolver.py",
        app_root / "module_registry" / "seed.py",
        app_root / "modules" / "companies" / "crud.py",
        app_root / "services" / "company_module_access.py",
    }
    needles = (
        "get_module_settings_snapshot(",
        ".settings.get(\"modules\")",
        ".settings.get('modules')",
        "settings.get(\"modules\")",
        "settings.get('modules')",
    )
    offenders: list[str] = []
    for path in app_root.rglob("*.py"):
        if "__pycache__" in path.parts or path in allowed:
            continue
        source = path.read_text(encoding="utf-8")
        if any(needle in source for needle in needles):
            offenders.append(str(path.relative_to(repo_root)))
    assert not offenders, (
        "New module availability checks must use backend.app.module_registry.resolver "
        f"instead of direct legacy tenant module flags. Offenders: {offenders}"
    )
