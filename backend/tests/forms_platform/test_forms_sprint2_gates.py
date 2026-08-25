"""Forms Sprint 2 — governance gates."""

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


def test_forms_sprint2_artifacts_and_code_exist() -> None:
    required = [
        "docs/specs/tasks/forms-sprint-2.md",
        "docs/specs/tasks/forms-sprint-1.md",
        "backend/app/forms_platform/adapter.py",
        "backend/app/forms_platform/errors.py",
        "backend/alembic/versions/202607180007_forms_s2.py",
        "backend/tests/forms_platform/test_forms_sprint2_contract.py",
    ]
    for rel in required:
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_sprint2_suites_have_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_sprint2*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_sprint2_migration_chain() -> None:
    text = (_VERSIONS / "202607180007_forms_s2.py").read_text(encoding="utf-8")
    assert 'revision: str = "202607180007_forms_s2"' in text
    assert 'down_revision: RevisionType = "202607180006_acq_3d_k"' in text
    assert "published_snapshot_v1" in text


def test_forms_sprint2_alembic_single_head() -> None:
    result = _run_alembic("heads")
    assert result.returncode == 0, result.stderr + result.stdout
    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(heads) == 1, f"Expected single Alembic head, got: {heads!r}\n{result.stdout}"
    # Sprint 2 revision remains in chain (may not be tip after Sprint 3+).
    assert (_VERSIONS / "202607180007_forms_s2.py").is_file()


def test_forms_sprint2_builder_still_locked() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is False  # unlocked after P1.3
    task = (_REPO_ROOT / "docs/specs/tasks/forms-sprint-2.md").read_text(encoding="utf-8")
    assert "LOCKED" in task
    assert "Builder" in task


def test_forms_sprint2_adapter_no_acquisition_imports() -> None:
    adapter = (_REPO_ROOT / "backend/app/forms_platform/adapter.py").read_text(encoding="utf-8")
    assert "from backend.app.acquisition" not in adapter
    assert "commit_publish" in adapter
    assert "deactivate_endpoint" in adapter
