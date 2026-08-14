"""Forms Platform C4 — Form Runtime Gate.

Runtime is not an engine. Adapter resolve DTO → Runtime Model only.
No Builder import, no lookup, no publish, no submit.
"""

from __future__ import annotations

import ast
import copy
import inspect
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from backend.app.forms_platform.contract_identity import freeze_contract_identity
from backend.app.forms_platform.errors import (
    FormsIdentityIncompleteError,
    FormsRuntimeNotPublicationError,
    FormsSchemaHashMismatchError,
)
from backend.app.forms_platform.runtime import RUNTIME_MODEL_CONTRACT, RuntimeModel, serve
from backend.app.forms_platform.schema import build_field_schema_v1

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNTIME_PKG = "backend.app.forms_platform.runtime"
_RUNTIME_DIR = _REPO_ROOT / "backend" / "app" / "forms_platform" / "runtime"
_BUILDER_DIR = _REPO_ROOT / "backend" / "app" / "forms_platform" / "builder"
_HISTORICAL_C4 = _REPO_ROOT / "backend" / "tests" / "forms_platform" / "test_forms_platform_c4.py"

_FORBIDDEN_MODULES = (
    "backend.app.forms_platform.builder",
    "backend.app.forms_platform.adapter",
    "backend.app.forms_platform.publication_versions",
    "backend.app.forms_platform.publication_bridge",
    "backend.app.forms_platform.submission_envelope",
    "backend.app.forms_platform.validation",
    "backend.app.forms_platform.answers",
    "backend.app.forms_platform.handlers",
    "backend.app.forms_platform.manifest",
)
_FORBIDDEN_ATTRS = frozenset(
    {
        "commit_publish",
        "publish",
        "save_session",
        "save_session_async",
        "persist_submission",
        "validate_submission",
        "resolve_forms_platform_publication",
        "get_publication_version",
        "append_publication_version",
        "freeze_contract_identity",
        "new_session",
        "FormDefinition",
    }
)


def _runtime_py_files() -> list[Path]:
    return sorted(_RUNTIME_DIR.glob("*.py"))


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
        "publication_id": "pub-1",
        "published_version": 2,
        "lifecycle_status": "active",
        "title": "Runtime Form",
        "public_slug": "runtime-form",
        "purpose": "inquiry",
        "consent_pin": {"terms_version": "t1"},
        "is_active": True,
        "has_immutable_snapshot": True,
        "field_schema": schema,
        "contract_identity": identity,
    }
    payload.update(overrides)
    return payload


def test_c4_runtime_does_not_import_builder_or_lookup_or_submit() -> None:
    for path in _runtime_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _resolved_imports(tree, pkg=_RUNTIME_PKG)
        for forbidden in _FORBIDDEN_MODULES:
            leaked_mod = [
                item
                for item in imported
                if item == forbidden or item.startswith(f"{forbidden}.")
            ]
            assert not leaked_mod, f"{path.name} imports {leaked_mod}"
        assert "backend.app.forms_platform" not in imported, (
            f"{path.name} imports package root (loads Adapter)"
        )
        used = _used_names(tree) | imported
        leak = used & _FORBIDDEN_ATTRS
        assert not leak, f"{path.name} references {sorted(leak)}"


def test_c4_builder_does_not_import_runtime() -> None:
    for path in sorted(_BUILDER_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _resolved_imports(tree, pkg="backend.app.forms_platform.builder")
        leaked = [
            item
            for item in imported
            if item == "backend.app.forms_platform.runtime"
            or item.startswith("backend.app.forms_platform.runtime.")
        ]
        assert not leaked, f"{path.name} imports Runtime {leaked}"
        used = _used_names(tree)
        assert "RuntimeModel" not in used
        assert "RUNTIME_MODEL_CONTRACT" not in used


def test_c4_serve_signature_is_publication_only() -> None:
    params = inspect.signature(serve).parameters
    assert list(params) == ["publication"]
    assert "db" not in params
    assert "form_id" not in params
    assert "public_slug" not in params
    assert inspect.iscoroutinefunction(serve) is False


def test_c4_serve_builds_runtime_model_from_frozen_publication() -> None:
    publication = _frozen_publication()
    model = serve(publication)
    assert isinstance(model, RuntimeModel)
    assert model.contract == RUNTIME_MODEL_CONTRACT
    assert model.form_id == "pub-1"
    assert model.published_version == 2
    assert dict(model.contract_identity) == publication["contract_identity"]
    assert dict(model.field_schema)["schema_contract"] == "forms.field_schema.v1"
    assert model.title == "Runtime Form"
    assert model.public_slug == "runtime-form"
    view = model.to_dict()
    assert view["contract"] == RUNTIME_MODEL_CONTRACT
    assert "builder_state" not in view
    assert "definition_id" not in view
    assert "submission" not in view


def test_c4_serve_is_read_only_copy() -> None:
    publication = _frozen_publication()
    model = serve(publication)
    publication["title"] = "mutated"
    publication["field_schema"]["fields"] = []
    publication["contract_identity"]["schema_hash"] = "deadbeef"
    assert model.title == "Runtime Form"
    assert dict(model.field_schema)["fields"]
    assert dict(model.contract_identity)["schema_hash"] != "deadbeef"
    with pytest.raises(TypeError):
        model.field_schema["fields"] = []  # type: ignore[index]


def test_c4_runtime_model_is_frozen() -> None:
    model = serve(_frozen_publication())
    with pytest.raises(FrozenInstanceError):
        model.title = "nope"  # type: ignore[misc]


def test_c4_draft_payload_is_not_servable() -> None:
    draft = {
        "definition_id": "def-1",
        "builder_state": "dirty",
        "draft_id": "def-1",
        "composition": {"instances": []},
        "published_version": 0,
    }
    with pytest.raises(FormsRuntimeNotPublicationError) as exc:
        serve(draft)
    assert exc.value.details.get("reason") == "authoring_payload"


def test_c4_missing_identity_fail_closed() -> None:
    publication = _frozen_publication()
    del publication["contract_identity"]
    with pytest.raises(FormsIdentityIncompleteError) as exc:
        serve(publication)
    assert exc.value.details.get("reason") == "runtime_requires_frozen_identity"


def test_c4_unpublished_payload_fail_closed() -> None:
    publication = _frozen_publication(published_version=0)
    with pytest.raises(FormsRuntimeNotPublicationError) as exc:
        serve(publication)
    assert exc.value.details.get("reason") == "unpublished"


def test_c4_schema_hash_mismatch_fail_closed() -> None:
    publication = _frozen_publication()
    other = build_field_schema_v1(fields=[{"id": "n.last", "type": "text", "required": False}])
    publication["field_schema"] = other
    with pytest.raises(FormsSchemaHashMismatchError):
        serve(publication)


def test_c4_does_not_re_mint_identity() -> None:
    publication = _frozen_publication()
    original = copy.deepcopy(publication["contract_identity"])
    model = serve(publication)
    assert dict(model.contract_identity) == original
    src = (_RUNTIME_DIR / "serve.py").read_text(encoding="utf-8")
    assert "freeze_contract_identity" not in src


def test_c4_historical_http_file_is_not_this_gate() -> None:
    assert _HISTORICAL_C4.exists()
    assert Path(__file__).name == "test_forms_c4_form_runtime_gate.py"
    assert Path(__file__).name != "test_forms_platform_c4.py"
