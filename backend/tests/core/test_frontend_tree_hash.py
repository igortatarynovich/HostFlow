"""OL-2A C-2: frontend identity is a content hash, not a directory name."""

from __future__ import annotations

import subprocess
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "deploy" / "frontend-tree-hash.sh"


def _hash(tree: Path) -> str:
    return subprocess.check_output(["bash", str(_SCRIPT), str(tree)], text=True).strip()


def test_frontend_tree_hash_stable_and_content_sensitive(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "index.html").write_text("<html>one</html>\n", encoding="utf-8")
    (b / "index.html").write_text("<html>one</html>\n", encoding="utf-8")
    assert _hash(a) == _hash(b)

    (b / "index.html").write_text("<html>two</html>\n", encoding="utf-8")
    assert _hash(a) != _hash(b)
