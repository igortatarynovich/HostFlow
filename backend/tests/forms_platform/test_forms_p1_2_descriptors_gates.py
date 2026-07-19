"""Forms Product Layer P1.2 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_XFAIL = re.compile(r"@pytest\.mark\.xfail")


def test_forms_p1_2_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p1-2-descriptors.md",
        "docs/specs/tasks/forms-product-p1-1-registry.md",
        "backend/app/forms_platform/field_catalog/descriptors.py",
        "backend/tests/forms_platform/test_forms_p1_2_descriptors_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p1_2_no_migration() -> None:
    versions = _REPO_ROOT / "backend" / "alembic" / "versions"
    assert list(versions.glob("*descriptor*")) == []
    assert list(versions.glob("*p1_2*")) == []
    assert list(versions.glob("*forms_p12*")) == []


def test_forms_p1_2_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p1_2*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p1_2_declarative_only_and_scope() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is False  # unlocked after P1.3
    text = (
        _REPO_ROOT / "backend/app/forms_platform/field_catalog/descriptors.py"
    ).read_text(encoding="utf-8")
    assert "DESCRIPTOR_CONTRACT" in text
    assert "callable" in text.lower()
    assert "eval(" not in text
    assert "exec(" not in text
    assert "from backend.app.acquisition" not in text
    # No UI / extension packages introduced in P1.2 itself
    pkg = _REPO_ROOT / "backend/app/forms_platform/field_catalog"
    assert not (pkg / "renderers.py").exists()
    # stdlib.py / extensions.py may exist after later sprints; must not appear in descriptors module
    assert "stdlib" not in text.lower()
    assert "register_extension" not in text
    task = (_REPO_ROOT / "docs/specs/tasks/forms-product-p1-2-descriptors.md").read_text(
        encoding="utf-8"
    )
    assert "declarative" in task.lower()
