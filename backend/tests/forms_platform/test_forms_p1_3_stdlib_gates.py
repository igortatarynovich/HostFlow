"""Forms Product Layer P1.3 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_XFAIL = re.compile(r"@pytest\.mark\.xfail")
_SPECIAL_CASE = re.compile(
    r'if\s+.*component_id\s*==\s*[\'"]forms\.field\.(email|phone|text)'
)


def test_forms_p1_3_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p1-3-standard-library.md",
        "docs/specs/tasks/forms-product-p1-2-descriptors.md",
        "backend/app/forms_platform/field_catalog/stdlib.py",
        "backend/tests/forms_platform/test_forms_p1_3_stdlib_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p1_3_no_migration() -> None:
    versions = _REPO_ROOT / "backend" / "alembic" / "versions"
    assert list(versions.glob("*stdlib*")) == []
    assert list(versions.glob("*p1_3*")) == []


def test_forms_p1_3_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p1_3*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p1_3_catalog_core_has_no_stdlib_special_cases() -> None:
    core = (
        _REPO_ROOT / "backend/app/forms_platform/field_catalog/registry.py",
        _REPO_ROOT / "backend/app/forms_platform/field_catalog/descriptors.py",
        _REPO_ROOT / "backend/app/forms_platform/field_catalog/versioning.py",
    )
    for path in core:
        text = path.read_text(encoding="utf-8")
        assert "forms.field.email" not in text, path.name
        assert "forms.field.phone" not in text, path.name
        assert _SPECIAL_CASE.search(text) is None, path.name
        assert "from backend.app.acquisition" not in text


def test_forms_p1_3_stdlib_is_catalog_client_only() -> None:
    stdlib = (
        _REPO_ROOT / "backend/app/forms_platform/field_catalog/stdlib.py"
    ).read_text(encoding="utf-8")
    assert "build_component_record" in stdlib
    assert "register(" in stdlib or "target.register" in stdlib
    assert "._by_key" not in stdlib
    assert "react" not in stdlib.lower()
    assert "extension api" not in stdlib.lower()
    # extensions.py is P1.4 — must not be imported/owned by stdlib
    assert "from backend.app.forms_platform.field_catalog.extensions" not in stdlib
    assert not (_REPO_ROOT / "backend/app/forms_platform/field_catalog/renderers.py").exists()


def test_forms_p1_3_builder_unlocked_sequence() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is False
    task = (_REPO_ROOT / "docs/specs/tasks/forms-product-p1-3-standard-library.md").read_text(
        encoding="utf-8"
    )
    assert "UNLOCKED" in task or "Builder" in task
    assert "P1.4" in task or "Extension" in task
