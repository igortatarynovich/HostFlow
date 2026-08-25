"""Forms Platform C6 — Optimization Gate.

Production Shared Intake: resolve → serve → execute. No second engine.
No Builder. No new Runtime contract. P3/P4/P5 stay locked.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.forms_platform.public_submit_bridge import (
    PUBLIC_APPLY_SUBMIT_PATH,
    hostflow_form_keys_from_intake_state,
    is_hostflow_form_public_submit,
    maybe_execute_hostflow_form_public_submit,
    payload_values_from_intake_state,
)
from backend.app.forms_platform.runtime import RUNTIME_MODEL_CONTRACT, serve

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIDGE = _REPO_ROOT / "backend" / "app" / "forms_platform" / "public_submit_bridge.py"
_INTAKE = _REPO_ROOT / "backend" / "app" / "api" / "public" / "intake.py"
_BRIDGE_PKG = "backend.app.forms_platform.public_submit_bridge"

_FORBIDDEN_MODULES = (
    "backend.app.forms_platform.builder",
    "backend.app.forms_platform.handlers",
    "backend.app.forms_platform.manifest",
)
_FORBIDDEN_ATTRS = frozenset(
    {
        "commit_publish",
        "publish",
        "save_session",
        "save_session_async",
        "new_session",
        "FormDefinition",
        "freeze_contract_identity",
    }
)


def _resolved_imports(tree: ast.AST, *, pkg: str) -> set[str]:
    found: set[str] = set()
    pkg_parts = pkg.split(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                parent = pkg_parts[: len(pkg_parts) - node.level]
                abs_mod = ".".join([*parent, node.module] if node.module else parent)
                found.add(abs_mod)
            elif node.module:
                found.add(node.module)
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
    return found


def _used_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def test_c6_bridge_does_not_import_builder_or_remint() -> None:
    src = _BRIDGE.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(_BRIDGE))
    imported = _resolved_imports(tree, pkg=_BRIDGE_PKG)
    for forbidden in _FORBIDDEN_MODULES:
        leaked = [
            item
            for item in imported
            if item == forbidden or item.startswith(f"{forbidden}.")
        ]
        assert not leaked, f"bridge imports {leaked}"
    used = _used_names(tree) | imported
    assert not (used & _FORBIDDEN_ATTRS)
    assert "freeze_contract_identity" not in src
    assert "APIRouter" not in src
    assert "/api/v1/platform/forms/submit" not in src


def test_c6_bridge_composes_resolve_serve_execute() -> None:
    src = _BRIDGE.read_text(encoding="utf-8")
    assert "resolve_publication" in src
    assert "serve" in src
    assert "persist_execution" in src
    params = inspect.signature(maybe_execute_hostflow_form_public_submit).parameters
    assert "tenant_id" in params
    assert "intake_state" in params
    assert inspect.iscoroutinefunction(maybe_execute_hostflow_form_public_submit) is True


def test_c6_public_intake_lead_draft_calls_bridge() -> None:
    src = _INTAKE.read_text(encoding="utf-8")
    assert "maybe_execute_hostflow_form_public_submit" in src
    assert "public_submit_bridge" in src
    # Existing Shared Intake apply-submit remains the write surface.
    assert '"/apply/{token}/submit"' in src or "'/apply/{token}/submit'" in src
    assert PUBLIC_APPLY_SUBMIT_PATH == "/api/v1/public/apply/{token}/submit"


def test_c6_unbound_intake_skips_execution() -> None:
    assert is_hostflow_form_public_submit({}) is False
    assert is_hostflow_form_public_submit({"lead_form": {}}) is False
    assert hostflow_form_keys_from_intake_state({"foo": 1}) == (None, None)


def test_c6_hostflow_form_detection_and_payload() -> None:
    state = {
        "lead_form": {"id": "form-1", "public_slug": "slug-1"},
        "presentation_values_v1": {"n.first": "Ada"},
    }
    assert is_hostflow_form_public_submit(state) is True
    assert hostflow_form_keys_from_intake_state(state) == ("form-1", "slug-1")
    assert payload_values_from_intake_state(state) == {"values": {"n.first": "Ada"}}


@pytest.mark.asyncio
async def test_c6_persist_binds_shared_intake_through_runtime_model() -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.forms_platform.adapter import commit_publish
    from backend.app.models.tenant_lead_form import TenantLeadForm
    from backend.tests.conftest import _init_data

    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="C6 Form",
                public_slug=f"c6-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
                published_version=1,
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        pub = await commit_publish(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            fields=[{"id": "n.first", "type": "text", "required": True}],
        )
        await session.commit()

    intake_state = {
        "lead_form": {"id": form_id, "public_slug": pub.get("public_slug")},
        "presentation_values_v1": {"n.first": "Ada"},
    }
    async with async_session_maker() as session:
        out = await maybe_execute_hostflow_form_public_submit(
            session,
            tenant_id=tenant_id,
            intake_state=intake_state,
            idempotency_key=f"c6-{form_id}",
        )
        await session.commit()

    assert out is not None
    assert out["ok"] is True
    assert out["form_id"] == form_id
    assert out["published_version"] == int(pub["published_version"])
    assert out["envelope"]["normalized_values"]["n.first"] == "Ada"
    # serve was on the path (Runtime Model contract)
    assert serve.__module__.endswith("forms_platform.runtime.serve")
    assert RUNTIME_MODEL_CONTRACT == "forms.runtime.model.v1"


@pytest.mark.asyncio
async def test_c6_non_hostflow_returns_none_without_resolve() -> None:
    from backend.app.db.session import async_session_maker
    from backend.tests.conftest import _init_data

    data = await _init_data()
    async with async_session_maker() as session:
        out = await maybe_execute_hostflow_form_public_submit(
            session,
            tenant_id=data["tenant_id"],
            intake_state={"application_kind": "candidate"},
        )
    assert out is None


def test_c6_gate_filename() -> None:
    assert Path(__file__).name == "test_forms_c6_optimization_gate.py"
