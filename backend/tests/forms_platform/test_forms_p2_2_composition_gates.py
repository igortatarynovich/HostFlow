"""Forms Product Layer P2.2 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMPOSITION = (
    _REPO_ROOT / "backend" / "app" / "forms_platform" / "builder" / "composition.py"
)
_XFAIL = re.compile(r"@pytest\.mark\.xfail")
_HARDCODE = re.compile(
    r'component_id\s*==\s*[\'"](?:forms\.field\.|email|phone|text)'
)


def test_forms_p2_2_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p2-2-composition-model.md",
        "docs/specs/tasks/forms-product-p2-builder.md",
        "backend/app/forms_platform/builder/composition.py",
        "backend/tests/forms_platform/test_forms_p2_2_composition_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p2_2_no_migration() -> None:
    versions = _REPO_ROOT / "backend" / "alembic" / "versions"
    assert list(versions.glob("*p2_2*")) == []
    assert list(versions.glob("*composition*")) == []


def test_forms_p2_2_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p2_2*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p2_2_no_stdlib_direct_import() -> None:
    text = _COMPOSITION.read_text(encoding="utf-8")
    assert "field_catalog.stdlib" not in text
    assert "from backend.app.forms_platform.field_catalog.stdlib" not in text


def test_forms_p2_2_no_hardcode_or_source_storage() -> None:
    text = _COMPOSITION.read_text(encoding="utf-8")
    assert _HARDCODE.search(text) is None
    assert "forms.field.email" not in text
    # Model forbids storing source; may mention it only as rejection
    assert "record.source" not in text
    assert ".is_platform" not in text


def test_forms_p2_2_no_persistence_or_ui() -> None:
    text = _COMPOSITION.read_text(encoding="utf-8")
    forbidden = (
        "sqlalchemy",
        "alembic",
        "APIRouter",
        "fastapi",
        "react",
        "save_draft",
        "load_draft",
        "commit_publish",
        "publish(",
    )
    lower = text.lower()
    for token in forbidden:
        assert token.lower() not in lower, token


def test_forms_p2_2_uses_public_catalog_get_only() -> None:
    text = _COMPOSITION.read_text(encoding="utf-8")
    assert ".get(" in text
    assert "._by_key" not in text
    assert ".register(" not in text
    assert "register_standard_library" not in text
    assert "register_extension" not in text


def test_forms_p2_2_catalog_untouched() -> None:
    for name in ("registry.py", "descriptors.py", "stdlib.py", "extensions.py"):
        core = (
            _REPO_ROOT / "backend/app/forms_platform/field_catalog" / name
        ).read_text(encoding="utf-8")
        assert "forms_platform.builder.composition" not in core
        assert "FormDraftComposition" not in core
