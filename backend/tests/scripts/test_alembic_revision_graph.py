"""Alembic revision-graph integrity gate (prevention for partial migration checkouts)."""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_revision_graph_passes_on_repo_versions() -> None:
    mod = _load("check_alembic_revision_graph.py")
    revisions = mod._collect_revisions(mod.DEFAULT_VERSIONS_DIR)
    assert revisions
    assert mod._missing_parents(revisions) == []
    assert len(mod._find_heads(revisions)) == 1


def test_missing_down_revision_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    versions = tmp_path / "versions"
    versions.mkdir()
    (versions / "child.py").write_text(
        textwrap.dedent(
            """
            revision = "child_rev"
            down_revision = "missing_parent"
            branch_labels = None
            depends_on = None
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    mod = _load("check_alembic_revision_graph.py")
    monkeypatch.setattr(mod, "DEFAULT_VERSIONS_DIR", versions)
    # argparse defaults are bound at call time via DEFAULT; invoke helpers.
    revisions = mod._collect_revisions(versions)
    missing = mod._missing_parents(revisions)
    assert missing == [("child_rev", "missing_parent")]

    # CLI must exit non-zero.
    monkeypatch.setattr(
        "sys.argv",
        ["check_alembic_revision_graph.py", "--versions-dir", str(versions), "--quiet"],
    )
    assert mod.main() == 2


def test_single_head_chain_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    versions = tmp_path / "versions"
    versions.mkdir()
    (versions / "a.py").write_text(
        'revision = "a"\ndown_revision = None\nbranch_labels = None\ndepends_on = None\n',
        encoding="utf-8",
    )
    (versions / "b.py").write_text(
        'revision = "b"\ndown_revision = "a"\nbranch_labels = None\ndepends_on = None\n',
        encoding="utf-8",
    )
    mod = _load("check_alembic_revision_graph.py")
    monkeypatch.setattr(
        "sys.argv",
        ["check_alembic_revision_graph.py", "--versions-dir", str(versions), "--quiet"],
    )
    assert mod.main() == 0
