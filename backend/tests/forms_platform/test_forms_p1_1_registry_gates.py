"""Forms Product Layer P1.1 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_XFAIL = re.compile(r"@pytest\.mark\.xfail")


def test_forms_p1_1_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p1-field-catalog.md",
        "docs/specs/tasks/forms-product-p1-1-registry.md",
        "backend/app/forms_platform/field_catalog/registry.py",
        "backend/app/forms_platform/field_catalog/versioning.py",
        "backend/tests/forms_platform/test_forms_p1_1_registry_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p1_1_no_migration() -> None:
    versions = _REPO_ROOT / "backend" / "alembic" / "versions"
    assert list(versions.glob("*field_catalog*")) == []
    assert list(versions.glob("*forms_p1*")) == []


def test_forms_p1_1_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p1_1*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p1_1_builder_locked_scope() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is False  # unlocked after P1.3
    pkg = _REPO_ROOT / "backend/app/forms_platform/field_catalog"
    for path in pkg.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "from backend.app.acquisition" not in text
        assert "def render_" not in text
        assert "BuilderUI" not in text
        assert "extension_api" not in text.lower()
    task = (_REPO_ROOT / "docs/specs/tasks/forms-product-p1-1-registry.md").read_text(
        encoding="utf-8"
    )
    assert "LOCKED" in task
    assert "Builder" in task
