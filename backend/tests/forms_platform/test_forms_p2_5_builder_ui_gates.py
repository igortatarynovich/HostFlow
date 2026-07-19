"""Forms Product Layer P2.5 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_XFAIL = re.compile(r"@pytest\.mark\.xfail")
_API = _REPO_ROOT / "backend/app/api/v1/platform/forms_builder.py"
_UI = _REPO_ROOT / "hostflow-frontend/src/pages/admin/FormsBuilderPage.tsx"


def test_forms_p2_5_docs_and_surfaces_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p2-5-minimal-builder-ui.md",
        "docs/specs/tasks/forms-product-p2-builder.md",
        "backend/app/api/v1/platform/forms_builder.py",
        "hostflow-frontend/src/pages/admin/FormsBuilderPage.tsx",
        "hostflow-frontend/src/api/formsBuilder.ts",
        "backend/tests/forms_platform/test_forms_p2_5_builder_ui_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p2_5_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p2_5*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p2_5_api_is_thin_catalog_client() -> None:
    text = _API.read_text(encoding="utf-8")
    assert "BuilderReadModel" in text
    assert "create_draft" in text or "update_draft" in text
    assert "commit_publish" not in text
    assert "field_catalog.stdlib" not in text
    assert "forms.field.email" not in text


def test_forms_p2_5_ui_minimal_scope() -> None:
    text = _UI.read_text(encoding="utf-8")
    assert "Palette" in text or "palette" in text
    assert "Canvas" in text or "canvas" in text
    assert "Save draft" in text or "save" in text.lower()
    assert "config_fields" in text
    for forbidden in (
        "theme editor",
        "publish wizard",
        "analytics",
        "conditional logic",
        "layout designer",
        "custom css",
        "public preview",
    ):
        assert forbidden not in text.lower(), forbidden


def test_forms_p2_5_ui_gate_complete_in_docs() -> None:
    task = (
        _REPO_ROOT / "docs/specs/tasks/forms-product-p2-builder.md"
    ).read_text(encoding="utf-8")
    assert "P2.5" in task
    assert "COMPLETE" in task or "READY" in task
