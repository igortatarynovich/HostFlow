"""Forms Product Layer P2.3 — governance gates."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMANDS = _REPO_ROOT / "backend" / "app" / "forms_platform" / "builder" / "commands.py"
_XFAIL = re.compile(r"@pytest\.mark\.xfail")
_HARDCODE = re.compile(
    r'component_id\s*==\s*[\'"](?:forms\.field\.|email|phone|text)'
)


def test_forms_p2_3_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-product-p2-3-composition-commands.md",
        "docs/specs/tasks/forms-product-p2-builder.md",
        "backend/app/forms_platform/builder/commands.py",
        "backend/tests/forms_platform/test_forms_p2_3_commands_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_p2_3_no_migration() -> None:
    versions = _REPO_ROOT / "backend" / "alembic" / "versions"
    assert list(versions.glob("*p2_3*")) == []
    assert list(versions.glob("*composition*command*")) == []


def test_forms_p2_3_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_p2_3*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_p2_3_no_stdlib_or_hardcode() -> None:
    text = _COMMANDS.read_text(encoding="utf-8")
    assert "field_catalog.stdlib" not in text
    assert _HARDCODE.search(text) is None
    assert "forms.field.email" not in text
    assert "BASIC_COMPONENT_IDS" not in text


def test_forms_p2_3_immutable_command_surface() -> None:
    text = _COMMANDS.read_text(encoding="utf-8")
    assert "def add_instance" in text
    assert "def remove_instance" in text
    assert "def reorder_instance" in text
    assert "def update_config" in text
    assert "def duplicate_instance" in text
    assert "def replace_component_version" in text
    # No persistence / publish / UI DnD
    for token in (
        "save_draft",
        "load_draft",
        "commit_publish",
        "sqlalchemy",
        "APIRouter",
        "on_drag",
        "drag_and_drop",
        "mousedown",
    ):
        assert token.lower() not in text.lower(), token


def test_forms_p2_3_uses_catalog_via_composition_builders() -> None:
    text = _COMMANDS.read_text(encoding="utf-8")
    assert "build_instance" in text
    assert ".register(" not in text
    assert "._by_key" not in text
    assert "register_standard_library" not in text


def test_forms_p2_3_catalog_untouched() -> None:
    for name in ("registry.py", "descriptors.py", "stdlib.py", "extensions.py"):
        core = (
            _REPO_ROOT / "backend/app/forms_platform/field_catalog" / name
        ).read_text(encoding="utf-8")
        assert "composition_commands" not in core
        assert "add_instance" not in core
