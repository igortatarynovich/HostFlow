"""Forms Product Layer P2.1 — governance gates."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUILDER_PKG = _REPO_ROOT / "backend" / "app" / "forms_platform" / "builder"
_XFAIL = re.compile(r"@pytest\.mark\.xfail")
_HARDCODE_ID = re.compile(
    r'component_id\s*==\s*[\'"](?:forms\.field\.|email|phone|text)'
)


def test_forms_p2_1_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p2-1-builder-read-model.md",
        "docs/specs/tasks/forms-product-p2-builder.md",
        "backend/app/forms_platform/builder/read_model.py",
        "backend/tests/forms_platform/test_forms_p2_1_read_model_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p2_1_no_migration() -> None:
    versions = _REPO_ROOT / "backend" / "alembic" / "versions"
    assert list(versions.glob("*p2_1*")) == []
    assert list(versions.glob("*builder*read*")) == []


def test_forms_p2_1_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p2_1*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p2_1_no_stdlib_direct_import() -> None:
    for path in _BUILDER_PKG.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "field_catalog.stdlib" not in text, path.name
        assert "from backend.app.forms_platform.field_catalog.stdlib" not in text
        assert "import stdlib" not in text


def test_forms_p2_1_no_component_id_hardcode() -> None:
    for path in _BUILDER_PKG.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert _HARDCODE_ID.search(text) is None, path.name
        assert "forms.field.email" not in text
        assert "forms.field.phone" not in text
        assert "BASIC_COMPONENT_IDS" not in text


def test_forms_p2_1_uses_public_catalog_apis_only() -> None:
    text = (_BUILDER_PKG / "read_model.py").read_text(encoding="utf-8")
    assert "platform_registry" in text or "FieldCatalogRegistry" in text
    assert ".find(" in text
    assert ".get(" in text or "get_descriptor" in text
    assert "._by_key" not in text
    assert ".register(" not in text
    assert "register_extension" not in text
    assert "register_standard_library" not in text
    assert "from backend.app.acquisition" not in text


def test_forms_p2_1_no_ui_or_later_sprint_surface() -> None:
    """P2.1 read_model surface only — later sprint modules are out of scope here."""
    forbidden = (
        "react",
        "jsx",
        "tsx",
        "vue",
        "fastapi",
        "APIRouter",
        "save_draft",
        "load_draft",
        "instance_id",
        "reorder_instance",
    )
    # Scope to P2.1 modules only (composition arrives in P2.2).
    paths = [
        _BUILDER_PKG / "read_model.py",
        _BUILDER_PKG / "__init__.py",
    ]
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        # __init__ may re-export later contracts; only enforce on read_model for model tokens
        check = forbidden if path.name == "read_model.py" else (
            "react",
            "jsx",
            "tsx",
            "vue",
            "fastapi",
            "APIRouter",
            "save_draft",
            "load_draft",
            "reorder_instance",
        )
        lower = text.lower()
        for token in check:
            assert token.lower() not in lower, f"{path.name} contains {token}"


def test_forms_p2_1_no_origin_branching_in_ast() -> None:
    """Working model must not branch on source / Basic vs extension."""
    path = _BUILDER_PKG / "read_model.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in {"source", "is_platform"}:
            raise AssertionError("read_model must not read ComponentRecord.source/is_platform")
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and comparator.value in {
                    "platform",
                    "module:",
                }:
                    raise AssertionError("read_model must not compare against origin literals")


def test_forms_p2_1_catalog_v1_untouched() -> None:
    freeze = (
        _REPO_ROOT / "docs/specs/architecture/forms-field-catalog-v1-freeze.md"
    ).read_text(encoding="utf-8")
    assert "FROZEN" in freeze
    # Core catalog modules must not import builder (Catalog stays independent)
    for name in ("registry.py", "descriptors.py", "stdlib.py", "extensions.py"):
        text = (
            _REPO_ROOT / "backend/app/forms_platform/field_catalog" / name
        ).read_text(encoding="utf-8")
        assert "forms_platform.builder" not in text, name
