"""Forms Sprint 4 — governance gates."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_VERSIONS = _BACKEND_ROOT / "alembic" / "versions"
_XFAIL = re.compile(r"@pytest\.mark\.xfail")


def _alembic_bin() -> str:
    for rel in (".venv312/bin/alembic", ".venv/bin/alembic"):
        candidate = _REPO_ROOT / rel
        if candidate.is_file():
            return str(candidate)
    return "alembic"


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for key in ("ALEMBIC_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_URL"):
        val = env.get(key)
        if val and "@db:" in val:
            env[key] = val.replace("@db:", "@127.0.0.1:")
    return subprocess.run(
        [_alembic_bin(), "-c", str(_BACKEND_ROOT / "alembic.ini"), *args],
        cwd=str(_BACKEND_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_forms_sprint4_docs_and_code_exist() -> None:
    required = [
        "docs/specs/tasks/forms-sprint-4.md",
        "docs/specs/tasks/forms-sprint-3.md",
        "backend/app/forms_platform/schema.py",
        "backend/app/forms_platform/validation.py",
        "backend/tests/forms_platform/test_forms_sprint4_contract.py",
    ]
    for rel in required:
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_sprint4_no_new_migration() -> None:
    forbidden = list(_VERSIONS.glob("*forms_s4*")) + list(_VERSIONS.glob("*sprint4*"))
    assert forbidden == [], forbidden


def test_forms_sprint4_alembic_single_head() -> None:
    result = _run_alembic("heads")
    assert result.returncode == 0, result.stderr + result.stdout
    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(heads) == 1, result.stdout


def test_forms_sprint4_suites_have_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_sprint4*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_sprint4_builder_still_locked() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is True
    task = (_REPO_ROOT / "docs/specs/tasks/forms-sprint-4.md").read_text(encoding="utf-8")
    assert "LOCKED" in task
    assert "Builder" in task


def test_forms_sprint4_no_outcome_kpi_ownership() -> None:
    for rel in (
        "backend/app/forms_platform/schema.py",
        "backend/app/forms_platform/validation.py",
    ):
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "outcome_service" not in text
        assert "kpi_aggregates" not in text
        assert "from backend.app.acquisition" not in text
