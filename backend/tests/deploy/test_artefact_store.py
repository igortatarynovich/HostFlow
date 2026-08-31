"""OL-2D: retained-digest store is immutable and named by digest."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

_STORE = Path(__file__).resolve().parents[3] / "scripts" / "deploy" / "artefact_store.py"
_SPEC = importlib.util.spec_from_file_location("artefact_store", _STORE)
assert _SPEC and _SPEC.loader
artefact_store = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(artefact_store)


def test_frontend_tree_hash_matches_shell(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    nested = tree / "assets"
    nested.mkdir(parents=True)
    (tree / "index.html").write_text("hello\n")
    (nested / "app.js").write_text("console.log(1)\n")
    script = _STORE.parent / "frontend-tree-hash.sh"
    shell = subprocess.check_output(["bash", str(script), str(tree)], text=True).strip()
    assert artefact_store.frontend_tree_hash(tree) == shell


def test_frontend_tree_hash_follows_locale_sort_not_codepoint(tmp_path: Path) -> None:
    tree = tmp_path / "mixed"
    tree.mkdir()
    (tree / "additional.js").write_text("a\n")
    (tree / "Candidate.js").write_text("b\n")
    assert artefact_store.frontend_tree_hash(tree) == subprocess.check_output(
        ["bash", str(_STORE.parent / "frontend-tree-hash.sh"), str(tree)],
        text=True,
    ).strip()


def test_frontend_tree_hash_stable_and_path_sensitive(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "index.html").write_text("hello\n")
    (a / "build.json").write_text('{"revision":"abc"}\n')
    (b / "index.html").write_text("hello\n")
    (b / "build.json").write_text('{"revision":"abc"}\n')
    first = artefact_store.frontend_tree_hash(a)
    assert first == artefact_store.frontend_tree_hash(b)
    (b / "build.json").rename(b / "BUILD.json")
    assert artefact_store.frontend_tree_hash(b) != first


def test_retain_is_idempotent_same_payload(tmp_path: Path) -> None:
    store = tmp_path / "store"
    blob = tmp_path / "one.tar"
    blob.write_bytes(b"payload-a")
    digest = "a" * 64
    first = artefact_store.retain_blob(store, "images", digest, blob)
    second = artefact_store.retain_blob(store, "images", digest, blob)
    assert first == second
    assert first.read_bytes() == b"payload-a"


def test_retain_refuses_different_payload_at_same_digest(tmp_path: Path) -> None:
    store = tmp_path / "store"
    first_blob = tmp_path / "one.tar"
    other_blob = tmp_path / "two.tar"
    first_blob.write_bytes(b"payload-a")
    other_blob.write_bytes(b"payload-b")
    digest = "b" * 64
    dest = artefact_store.retain_blob(store, "frontend", digest, first_blob)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        artefact_store.retain_blob(store, "frontend", digest, other_blob)
    assert dest.read_bytes() == b"payload-a"


def test_missing_blob_path_is_the_failure_signal(tmp_path: Path) -> None:
    store = tmp_path / "store"
    path = artefact_store.blob_path(store, "images", "c" * 64)
    assert not path.exists()
    assert path.name == ("c" * 64) + ".tar"


def test_manifest_refuses_identity_drift(tmp_path: Path) -> None:
    store = tmp_path / "store"
    args = dict(
        revision="11f1c84586c0e96538e7a27e0d14c1617d5a3a8f",
        backend_image_id="d" * 64,
        frontend_tree_hash_value="e" * 64,
        alembic_head="202608310001_bootstrap_admin_schema",
    )
    dest = artefact_store.write_manifest(store, **args)
    artefact_store.write_manifest(store, **args)
    drifted = dict(args)
    drifted["alembic_head"] = "202608250002_merge_e5_drop_and_adr036_heads"
    with pytest.raises(FileExistsError, match="refusing to overwrite manifest"):
        artefact_store.write_manifest(store, **drifted)
    body = json.loads(dest.read_text())
    assert body["backend_image_id"] == "sha256:" + ("d" * 64)
    assert body["alembic_head"] == "202608310001_bootstrap_admin_schema"
