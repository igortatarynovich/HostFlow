"""Forms Platform C5 — Form Execution Gate.

Runtime Model → Validation → Submission → Persistence.
No Builder import, no publish, no identity re-mint, no second submit engine.
"""

from __future__ import annotations

import ast
import copy
import inspect
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.forms_platform.contract_identity import freeze_contract_identity
from backend.app.forms_platform.errors import (
    FormsArchivedError,
    FormsExecutionRequiresRuntimeModelError,
    FormsIdentityIncompleteError,
    FormsInactiveError,
    FormsSchemaHashMismatchError,
)
from backend.app.forms_platform.execution import (
    PUBLIC_INTAKE_PATH,
    execute_submission,
    persist_execution,
    submission_pin,
    validate_against_runtime_model,
)
from backend.app.forms_platform.runtime import RUNTIME_MODEL_CONTRACT, RuntimeModel, serve
from backend.app.forms_platform.schema import build_field_schema_v1
from backend.app.forms_platform.validation import FormsValidationError

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EXECUTION_PKG = "backend.app.forms_platform.execution"
_EXECUTION_DIR = _REPO_ROOT / "backend" / "app" / "forms_platform" / "execution"
_RUNTIME_DIR = _REPO_ROOT / "backend" / "app" / "forms_platform" / "runtime"
_BUILDER_DIR = _REPO_ROOT / "backend" / "app" / "forms_platform" / "builder"

_FORBIDDEN_MODULES = (
    "backend.app.forms_platform.builder",
    "backend.app.forms_platform.adapter",
    "backend.app.forms_platform.publication_bridge",
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
        "resolve_forms_platform_publication",
        "get_publication_version",
        "append_publication_version",
    }
)


def _execution_py_files() -> list[Path]:
    return sorted(_EXECUTION_DIR.glob("*.py"))


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


def _frozen_publication(**overrides: object) -> dict:
    schema = build_field_schema_v1(
        fields=[{"id": "n.first", "type": "text", "required": True}]
    )
    identity = freeze_contract_identity(schema).to_dict()
    payload: dict = {
        "publication_id": "pub-c5",
        "published_version": 3,
        "lifecycle_status": "active",
        "title": "Execution Form",
        "public_slug": "execution-form",
        "purpose": "inquiry",
        "consent_pin": {"terms_version": "t1"},
        "is_active": True,
        "has_immutable_snapshot": True,
        "field_schema": schema,
        "contract_identity": identity,
    }
    payload.update(overrides)
    return payload


def test_c5_execution_does_not_import_builder_or_publish_surface() -> None:
    for path in _execution_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _resolved_imports(tree, pkg=_EXECUTION_PKG)
        for forbidden in _FORBIDDEN_MODULES:
            leaked_mod = [
                item
                for item in imported
                if item == forbidden or item.startswith(f"{forbidden}.")
            ]
            assert not leaked_mod, f"{path.name} imports {leaked_mod}"
        assert "backend.app.forms_platform" not in imported, (
            f"{path.name} imports package root (loads Adapter publish)"
        )
        used = _used_names(tree) | imported
        leak = used & _FORBIDDEN_ATTRS
        assert not leak, f"{path.name} references {sorted(leak)}"
        src = path.read_text(encoding="utf-8")
        assert "freeze_contract_identity" not in src


def test_c5_runtime_still_does_not_import_execution() -> None:
    for path in sorted(_RUNTIME_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _resolved_imports(tree, pkg="backend.app.forms_platform.runtime")
        leaked = [
            item
            for item in imported
            if item == "backend.app.forms_platform.execution"
            or item.startswith("backend.app.forms_platform.execution.")
        ]
        assert not leaked, f"{path.name} imports Execution {leaked}"
        used = _used_names(tree)
        assert "execute_submission" not in used
        assert "persist_execution" not in used


def test_c5_builder_does_not_import_execution() -> None:
    for path in sorted(_BUILDER_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _resolved_imports(tree, pkg="backend.app.forms_platform.builder")
        leaked = [
            item
            for item in imported
            if item == "backend.app.forms_platform.execution"
            or item.startswith("backend.app.forms_platform.execution.")
        ]
        assert not leaked, f"{path.name} imports Execution {leaked}"


def test_c5_validate_signature_is_runtime_model_only() -> None:
    params = inspect.signature(validate_against_runtime_model).parameters
    assert list(params)[0] == "model"
    assert "publication" not in params
    assert "db" not in params
    assert "FormDefinition" not in params
    assert inspect.iscoroutinefunction(validate_against_runtime_model) is False


def test_c5_execute_validates_against_runtime_model() -> None:
    model = serve(_frozen_publication())
    assert isinstance(model, RuntimeModel)
    assert model.contract == RUNTIME_MODEL_CONTRACT
    result = execute_submission(model, {"values": {"n.first": "Ada"}})
    assert result["ok"] is True
    assert result["public_intake_path"] == PUBLIC_INTAKE_PATH
    assert result["public_intake_path"] == "/api/v1/public/intake"
    assert result["form_id"] == "pub-c5"
    assert result["published_version"] == 3
    assert result["submission_pin"]["publication_version_pin"]["version"] == 3
    assert result["contract_identity"] == dict(model.contract_identity)
    assert result["answer"]["normalized_values"]["n.first"] == "Ada"
    assert "builder_state" not in result
    assert "definition_id" not in result


def test_c5_rejects_non_runtime_model() -> None:
    with pytest.raises(FormsExecutionRequiresRuntimeModelError) as exc:
        validate_against_runtime_model(  # type: ignore[arg-type]
            _frozen_publication(),
            {"values": {"n.first": "Ada"}},
        )
    assert exc.value.details.get("reason") == "runtime_model_required"


def test_c5_rejects_draft_shaped_input() -> None:
    draft = {
        "definition_id": "def-1",
        "builder_state": "dirty",
        "draft_id": "def-1",
        "composition": {"instances": []},
        "published_version": 0,
    }
    with pytest.raises(FormsExecutionRequiresRuntimeModelError):
        execute_submission(draft, {"values": {"n.first": "Ada"}})  # type: ignore[arg-type]


def test_c5_inactive_and_archived_fail_closed() -> None:
    inactive = serve(_frozen_publication(is_active=False))
    with pytest.raises(FormsInactiveError):
        validate_against_runtime_model(inactive, {"values": {"n.first": "Ada"}})
    archived = serve(_frozen_publication(lifecycle_status="archived"))
    with pytest.raises(FormsArchivedError):
        submission_pin(archived)


def test_c5_identity_mismatch_fail_closed() -> None:
    publication = _frozen_publication()
    model = serve(publication)
    # Bypass frozen dataclass via object.__setattr__ is forbidden; mutate copy path:
    broken = RuntimeModel(
        contract=model.contract,
        form_id=model.form_id,
        published_version=model.published_version,
        contract_identity=model.contract_identity,
        field_schema=build_field_schema_v1(
            fields=[{"id": "n.last", "type": "text", "required": False}]
        ),
        lifecycle_status=model.lifecycle_status,
        title=model.title,
        public_slug=model.public_slug,
        purpose=model.purpose,
        consent_pin=model.consent_pin,
        is_active=model.is_active,
    )
    with pytest.raises(FormsSchemaHashMismatchError):
        validate_against_runtime_model(broken, {"values": {"n.last": "X"}})


def test_c5_missing_identity_fail_closed() -> None:
    model = serve(_frozen_publication())
    broken = RuntimeModel(
        contract=model.contract,
        form_id=model.form_id,
        published_version=model.published_version,
        contract_identity={},
        field_schema=model.field_schema,
        lifecycle_status=model.lifecycle_status,
        title=model.title,
        public_slug=model.public_slug,
        purpose=model.purpose,
        consent_pin=model.consent_pin,
        is_active=model.is_active,
    )
    with pytest.raises(FormsIdentityIncompleteError) as exc:
        validate_against_runtime_model(broken, {"values": {"n.first": "Ada"}})
    assert exc.value.details.get("reason") == "execution_requires_frozen_identity"


def test_c5_does_not_re_mint_identity() -> None:
    publication = _frozen_publication()
    original = copy.deepcopy(publication["contract_identity"])
    model = serve(publication)
    result = execute_submission(model, {"values": {"n.first": "Ada"}})
    assert result["contract_identity"] == original
    for path in _execution_py_files():
        assert "freeze_contract_identity" not in path.read_text(encoding="utf-8")


def test_c5_validation_errors_surface() -> None:
    model = serve(_frozen_publication())
    with pytest.raises(FormsValidationError):
        validate_against_runtime_model(
            model, {"values": {}}, raise_on_error=True
        )


def test_c5_no_second_submit_http_in_execution() -> None:
    for path in _execution_py_files():
        src = path.read_text(encoding="utf-8")
        assert "/api/v1/platform/forms/submit" not in src
        assert "APIRouter" not in src
        assert "@router" not in src
    assert PUBLIC_INTAKE_PATH == "/api/v1/public/intake"


@pytest.mark.asyncio
async def test_c5_persist_binds_runtime_model_to_shared_intake_envelope() -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.forms_platform.adapter import commit_publish, resolve_publication
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
                title="C5 Form",
                public_slug=f"c5-{form_id[:8]}",
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

    async with async_session_maker() as session:
        resolved = await resolve_publication(
            session, tenant_id=tenant_id, form_id=form_id, version=int(pub["published_version"])
        )
        model = serve(resolved)
        out = await persist_execution(
            session,
            tenant_id=tenant_id,
            model=model,
            payload={"values": {"n.first": "Ada"}},
            raise_on_error=True,
        )
        await session.commit()

    assert out["ok"] is True
    assert out["public_intake_path"] == PUBLIC_INTAKE_PATH
    assert out["envelope"]["publication_version_pin"]["version"] == model.published_version
    assert out["envelope"]["contract_identity"] == dict(model.contract_identity)
    assert out["envelope"]["normalized_values"]["n.first"] == "Ada"


def test_c5_gate_filename() -> None:
    assert Path(__file__).name == "test_forms_c5_form_execution_gate.py"
