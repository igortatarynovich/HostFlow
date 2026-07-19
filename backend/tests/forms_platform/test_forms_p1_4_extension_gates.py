"""Forms Product Layer P1.4 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_XFAIL = re.compile(r"@pytest\.mark\.xfail")


def test_forms_p1_4_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p1-4-extension-api.md",
        "docs/specs/tasks/forms-product-p1-3-standard-library.md",
        "docs/specs/architecture/forms-field-catalog-v1-freeze.md",
        "backend/app/forms_platform/field_catalog/extensions.py",
        "backend/tests/forms_platform/test_forms_p1_4_extension_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p1_4_no_migration_no_tenant() -> None:
    versions = _REPO_ROOT / "backend" / "alembic" / "versions"
    assert list(versions.glob("*forms*p1_4*")) == []
    assert list(versions.glob("*field_catalog*extension*")) == []
    text = (
        _REPO_ROOT / "backend/app/forms_platform/field_catalog/extensions.py"
    ).read_text(encoding="utf-8")
    assert "no tenant packs" in text.lower() or "tenant" in text.lower()
    assert "tenant_id" not in text


def test_forms_p1_4_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p1_4*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p1_4_uses_public_apis_only() -> None:
    text = (
        _REPO_ROOT / "backend/app/forms_platform/field_catalog/extensions.py"
    ).read_text(encoding="utf-8")
    assert "build_component_record" in text
    assert "target.register" in text or ".register(" in text
    assert "._by_key" not in text
    assert "from backend.app.acquisition" not in text
    # Core files must not special-case module ids
    for name in ("registry.py", "descriptors.py", "versioning.py"):
        core = (_REPO_ROOT / "backend/app/forms_platform/field_catalog" / name).read_text(
            encoding="utf-8"
        )
        assert "recruitment.field" not in core
        assert "module:recruitment" not in core


def test_forms_p1_4_v1_freeze_and_p2_ready() -> None:
    freeze = (
        _REPO_ROOT / "docs/specs/architecture/forms-field-catalog-v1-freeze.md"
    ).read_text(encoding="utf-8")
    assert "FROZEN" in freeze or "freeze" in freeze.lower()
    assert "forms.field_catalog.registry.v1" in freeze
    assert "forms.field_catalog.descriptors.v1" in freeze
    assert "forms.field_catalog.stdlib.v1" in freeze
    assert "forms.field_catalog.extension.v1" in freeze
    task = (_REPO_ROOT / "docs/specs/tasks/forms-product-p1-4-extension-api.md").read_text(
        encoding="utf-8"
    )
    assert "P2" in task or "Builder" in task
