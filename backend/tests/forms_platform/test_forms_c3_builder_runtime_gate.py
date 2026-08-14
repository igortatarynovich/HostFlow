"""Forms Platform C3 — Builder Runtime Gate.

Builder mutates FormDefinition ↔ Draft only. No Adapter, publish, identity, resolve.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.forms_platform.builder.composition import build_composition, build_instance
from backend.app.forms_platform.builder.definition import (
    BUILDER_DEFINITION_CONTRACT,
    FormDefinition,
)
from backend.app.forms_platform.builder.draft_persistence import InMemoryDraftStore
from backend.app.forms_platform.builder.session import (
    close_session,
    edit_session,
    new_session,
    save_session,
    session_from_error,
    session_from_record,
)
from backend.app.forms_platform.builder.state import (
    BUILDER_STATES,
    EVENT_BEGIN_SAVE,
    EVENT_CLOSE,
    EVENT_EDIT,
    EVENT_SAVE_CONFLICT,
    EVENT_SAVE_OK,
    EVENT_SAVE_VALIDATION_ERROR,
    MUTABLE_DRAFT_STATES,
    STATE_CLOSED,
    STATE_CONFLICT,
    STATE_DIRTY,
    STATE_NEW,
    STATE_SAVED,
    STATE_SAVING,
    STATE_VALIDATION_ERROR,
    transition,
)
from backend.app.forms_platform.errors import (
    FormsBuilderCompositionInvalidError,
    FormsBuilderDraftConflictError,
    FormsBuilderDraftNotFoundError,
    FormsBuilderStateError,
)
from backend.app.forms_platform.field_catalog import FieldCatalogRegistry, register_standard_library

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUILDER_PKG = "backend.app.forms_platform.builder"
_BUILDER_DIR = _REPO_ROOT / "backend" / "app" / "forms_platform" / "builder"
_HTTP_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "platform" / "forms_builder.py"

_FORBIDDEN_MODULES = (
    "backend.app.forms_platform.adapter",
    "backend.app.forms_platform.publication_versions",
    "backend.app.forms_platform.publication_bridge",
    "backend.app.forms_platform.contract_identity",
    "backend.app.forms_platform.submission_envelope",
    "backend.app.forms_platform.canonical",
    "backend.app.forms_platform.compatibility",
)
_FORBIDDEN_ATTRS = frozenset(
    {
        "commit_publish",
        "resolve_publication",
        "publish",
        "schema_hash",
        "schema_hash_sha256",
        "freeze_contract_identity",
        "resolve_endpoint",
    }
)


def _builder_py_files() -> list[Path]:
    return sorted(_BUILDER_DIR.glob("*.py"))


def _resolved_imports(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    pkg_parts = _BUILDER_PKG.split(".")
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


def test_c3_builder_does_not_import_adapter_or_publication_runtime() -> None:
    for path in _builder_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = _resolved_imports(tree)
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


def test_c3_builder_state_machine_closed_set() -> None:
    assert BUILDER_STATES == {
        "new",
        "dirty",
        "saving",
        "saved",
        "validation_error",
        "conflict",
        "closed",
    }
    assert MUTABLE_DRAFT_STATES <= BUILDER_STATES
    assert "saved" in MUTABLE_DRAFT_STATES
    assert "dirty" in MUTABLE_DRAFT_STATES
    assert "validation_error" in MUTABLE_DRAFT_STATES
    assert "conflict" in MUTABLE_DRAFT_STATES
    assert "closed" not in MUTABLE_DRAFT_STATES
    assert "saving" not in MUTABLE_DRAFT_STATES
    assert transition(STATE_NEW, EVENT_EDIT) == STATE_DIRTY
    assert transition(STATE_DIRTY, EVENT_BEGIN_SAVE) == STATE_SAVING
    assert transition(STATE_SAVING, EVENT_SAVE_OK) == STATE_SAVED
    assert transition(STATE_SAVING, EVENT_SAVE_VALIDATION_ERROR) == STATE_VALIDATION_ERROR
    assert transition(STATE_SAVING, EVENT_SAVE_CONFLICT) == STATE_CONFLICT
    assert transition(STATE_SAVED, EVENT_EDIT) == STATE_DIRTY
    assert transition(STATE_VALIDATION_ERROR, EVENT_EDIT) == STATE_DIRTY
    assert transition(STATE_CONFLICT, EVENT_EDIT) == STATE_DIRTY
    assert transition(STATE_SAVED, EVENT_CLOSE) == STATE_CLOSED
    with pytest.raises(FormsBuilderStateError):
        transition(STATE_CLOSED, EVENT_EDIT)
    with pytest.raises(FormsBuilderStateError):
        transition(STATE_SAVING, EVENT_EDIT)
    with pytest.raises(FormsBuilderStateError):
        transition(STATE_VALIDATION_ERROR, EVENT_BEGIN_SAVE)
    with pytest.raises(FormsBuilderStateError):
        transition(STATE_CONFLICT, EVENT_BEGIN_SAVE)


def test_c3_form_definition_is_only_mutable_document() -> None:
    assert BUILDER_DEFINITION_CONTRACT == "forms.builder.form_definition.v1"
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    composition = build_composition(draft_id="def-1", instances=[], registry=registry)
    definition = FormDefinition(definition_id="def-1", composition=composition)
    assert definition.definition_id == "def-1"
    session = new_session(tenant_id="t1", composition=composition)
    assert session.state == STATE_NEW
    assert session.definition.definition_id == "def-1"
    dirty = edit_session(session, composition)
    assert dirty.state == STATE_DIRTY
    store = InMemoryDraftStore()
    saved = save_session(dirty, store, registry=registry)
    assert saved.state == STATE_SAVED
    assert saved.revision == 1
    assert store.get(tenant_id="t1", draft_id="def-1").revision == 1
    assert not hasattr(store, "publication_versions")
    closed = close_session(saved)
    assert closed.state == STATE_CLOSED


def test_c3_save_draft_does_not_mint_publication_identity() -> None:
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    composition = build_composition(draft_id="d-save", instances=[], registry=registry)
    session = new_session(tenant_id="t1", composition=composition)
    store = InMemoryDraftStore()
    saved = save_session(session, store, registry=registry)
    record = store.get(tenant_id="t1", draft_id="d-save")
    payload = record.to_dict()
    assert "contract_identity" not in payload
    assert "schema_hash" not in payload
    assert "schema_hash" not in record.composition
    assert saved.state == STATE_SAVED
    dirty = edit_session(saved, composition)
    saved2 = save_session(dirty, store, registry=registry)
    assert saved2.revision == 2
    assert store.get(tenant_id="t1", draft_id="d-save").status == "active"


def test_c3_unknown_catalog_component_fails_closed_as_validation_error() -> None:
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    bad = build_composition(
        draft_id="bad-catalog",
        instances=[
            build_instance(
                component_id="forms.field.text",
                component_version="9.9.9",
                require_catalog=False,
            )
        ],
        require_valid=False,
    )
    session = new_session(tenant_id="t1", composition=bad)
    store = InMemoryDraftStore()
    with pytest.raises(FormsBuilderCompositionInvalidError) as excinfo:
        save_session(session, store, registry=registry)
    failed = session_from_error(excinfo.value)
    assert failed is not None
    assert failed.state == STATE_VALIDATION_ERROR
    assert excinfo.value.details.get("builder_state") == STATE_VALIDATION_ERROR
    with pytest.raises(FormsBuilderDraftNotFoundError):
        store.get(tenant_id="t1", draft_id="bad-catalog")
    recovered = edit_session(failed, bad)
    assert recovered.state == STATE_DIRTY


def test_c3_revision_conflict_stays_draft_not_publication() -> None:
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    composition = build_composition(draft_id="d-conflict", instances=[], registry=registry)
    session = new_session(tenant_id="t1", composition=composition)
    store = InMemoryDraftStore()
    saved = save_session(session, store, registry=registry)
    stale = replace(saved, revision=99)
    with pytest.raises(FormsBuilderDraftConflictError) as excinfo:
        save_session(stale, store, registry=registry)
    failed = session_from_error(excinfo.value)
    assert failed is not None
    assert failed.state == STATE_CONFLICT
    tip = store.get(tenant_id="t1", draft_id="d-conflict")
    assert tip.revision == 1
    assert "contract_identity" not in tip.to_dict()
    recovered = edit_session(failed, composition)
    assert recovered.state == STATE_DIRTY


def test_c3_session_from_saved_record_stays_mutable_draft() -> None:
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    composition = build_composition(draft_id="d-load", instances=[], registry=registry)
    store = InMemoryDraftStore()
    saved = save_session(new_session(tenant_id="t1", composition=composition), store, registry=registry)
    record = store.get(tenant_id="t1", draft_id="d-load")
    loaded = session_from_record(tenant_id="t1", record=record)
    assert loaded.state == STATE_SAVED
    assert loaded.definition.definition_id == "d-load"
    dirty = edit_session(loaded, composition)
    assert dirty.state == STATE_DIRTY
    closed = close_session(loaded)
    assert closed.state == STATE_CLOSED
    with pytest.raises(FormsBuilderStateError):
        edit_session(closed, composition)


def test_c3_builder_http_save_is_form_definition_not_publish() -> None:
    tree = ast.parse(_HTTP_API.read_text(encoding="utf-8"), filename=str(_HTTP_API))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    for forbidden in _FORBIDDEN_MODULES:
        assert forbidden not in imported, f"HTTP imports {forbidden}"
    text = _HTTP_API.read_text(encoding="utf-8")
    assert "FormDefinition" in text
    assert "save_session_async" in text
    assert "commit_publish" not in text
    assert "resolve_publication" not in text
    used = _used_names(tree)
    assert not (used & {"commit_publish", "resolve_publication", "freeze_contract_identity"})
