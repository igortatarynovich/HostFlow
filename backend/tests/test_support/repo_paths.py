"""Repo-anchored paths for tests that assert on source text.

Such tests must not depend on the working directory pytest was started from:
`AGENTS.md` documents running from `backend/`, while CI and several local
recipes run from the repo root, and a repo-relative literal only works in one
of the two.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def repo_path(relative: str) -> Path:
    """Return an absolute path for a repo-relative location such as ``backend/app/main.py``."""
    return REPO_ROOT / relative


def read_repo_text(relative: str) -> str:
    """Read a repo-relative source file as UTF-8 text."""
    return repo_path(relative).read_text(encoding="utf-8")


def alembic_executable() -> str | None:
    """Locate the Alembic CLI independently of which venv the worktree owns.

    Worktrees often lack ``.venv312``; pytest still runs from another checkout's
    venv. Prefer that interpreter's ``bin/alembic`` over a missing local script.
    """
    candidates = [
        REPO_ROOT / ".venv312" / "bin" / "alembic",
        REPO_ROOT / ".venv" / "bin" / "alembic",
        # Do not Path.resolve() the interpreter: venv python is often a symlink to
        # the system python, which would send us to /usr/bin/alembic.
        Path(sys.executable).parent / "alembic",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("alembic")
