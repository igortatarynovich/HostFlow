"""Forms Product Layer P2.4 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PERSIST = (
    _REPO_ROOT / "backend" / "app" / "forms_platform" / "builder" / "draft_persistence.py"
)
_XFAIL = re.compile(r"@pytest\.mark\.xfail")
_HARDCODE = re.compile(
    r'component_id\s*==\s*[\'"](?:forms\.field\.|email|phone|text)'
)


def test_forms_p2_4_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p2-4-draft-persistence.md",
        "docs/specs/tasks/forms-product-p2-builder.md",
        "backend/app/forms_platform/builder/draft_persistence.py",
        "backend/app/models/form_builder_draft.py",
        "backend/alembic/versions/202607190001_forms_p24.py",
        "backend/tests/forms_platform/test_forms_p2_4_draft_persistence_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p2_4_migration_chain() -> None:
    text = (
        _REPO_ROOT / "backend/alembic/versions/202607190001_forms_p24.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "202607190001_forms_p24"' in text
    assert 'down_revision: RevisionType = "202607180009_forms_s6"' in text
    assert "form_builder_drafts" in text
    assert "form_builder_draft_revisions" in text


def test_forms_p2_4_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p2_4*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p2_4_no_hardcode_or_stdlib() -> None:
    text = _PERSIST.read_text(encoding="utf-8")
    assert "field_catalog.stdlib" not in text
    assert _HARDCODE.search(text) is None
    assert "forms.field.email" not in text


def test_forms_p2_4_no_publish_or_intake_or_ui() -> None:
    text = _PERSIST.read_text(encoding="utf-8")
    for token in (
        "commit_publish",
        "published_snapshot",
        "intake_handoff",
        "APIRouter",
        "react",
        "drag_and_drop",
        "domain_mapping",
    ):
        assert token not in text, token


def test_forms_p2_4_uses_composition_contract_untransformed() -> None:
    text = _PERSIST.read_text(encoding="utf-8")
    assert "BUILDER_COMPOSITION_CONTRACT" in text
    assert "composition.to_dict()" in text or "to_dict()" in text
    assert "parse_composition" in text
    assert "assert_valid" in text


def test_forms_p2_4_catalog_and_publication_untouched() -> None:
    for name in ("registry.py", "stdlib.py", "extensions.py"):
        core = (
            _REPO_ROOT / "backend/app/forms_platform/field_catalog" / name
        ).read_text(encoding="utf-8")
        assert "draft_persistence" not in core
        assert "FormBuilderDraft" not in core
    adapter = (
        _REPO_ROOT / "backend/app/forms_platform/adapter.py"
    ).read_text(encoding="utf-8")
    assert "FormBuilderDraft" not in adapter
    assert "draft_persistence" not in adapter


def test_forms_p2_4_ui_gate_docs_ready() -> None:
    task = (
        _REPO_ROOT / "docs/specs/tasks/forms-product-p2-builder.md"
    ).read_text(encoding="utf-8")
    assert "P2.4" in task
    assert "P2.5" in task
    assert "UI start gate" in task or "UI gate" in task
