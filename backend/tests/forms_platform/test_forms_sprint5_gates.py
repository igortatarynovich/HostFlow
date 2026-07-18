"""Forms Sprint 5 — governance gates."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_VERSIONS = _BACKEND_ROOT / "alembic" / "versions"
_XFAIL = re.compile(r"@pytest\.mark\.xfail")


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for key in ("ALEMBIC_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_URL"):
        val = env.get(key)
        if val and "@db:" in val:
            env[key] = val.replace("@db:", "@127.0.0.1:")
    alembic = None
    for rel in (".venv312/bin/alembic", ".venv/bin/alembic"):
        cand = _REPO_ROOT / rel
        if cand.is_file():
            alembic = str(cand)
            break
    if alembic is None:
        alembic = "alembic"
    return subprocess.run(
        [alembic, "-c", str(_BACKEND_ROOT / "alembic.ini"), *args],
        cwd=str(_BACKEND_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_forms_sprint5_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-sprint-5.md",
        "docs/specs/tasks/forms-sprint-4.md",
        "backend/app/forms_platform/answers.py",
        "backend/tests/forms_platform/test_forms_sprint5_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_sprint5_no_new_migration() -> None:
    assert list(_VERSIONS.glob("*forms_s5*")) + list(_VERSIONS.glob("*sprint5*")) == []


def test_forms_sprint5_alembic_single_head() -> None:
    result = _run_alembic("heads")
    assert result.returncode == 0, result.stderr + result.stdout
    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(heads) == 1, result.stdout


def test_forms_sprint5_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_sprint5*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None


def test_forms_sprint5_builder_locked_and_no_domain_mapping() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is True
    answers = (_REPO_ROOT / "backend/app/forms_platform/answers.py").read_text(encoding="utf-8")
    assert "from backend.app.acquisition" not in answers
    assert "Candidate" not in answers
    assert "domain mapping" in answers.lower() or "No domain" in answers
    task = (_REPO_ROOT / "docs/specs/tasks/forms-sprint-5.md").read_text(encoding="utf-8")
    assert "LOCKED" in task
    assert "Builder" in task
