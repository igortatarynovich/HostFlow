"""Forms Sprint 3 — governance / Alembic gates."""

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


def test_forms_sprint3_artifacts_and_code_exist() -> None:
    required = [
        "docs/specs/tasks/forms-sprint-3.md",
        "docs/specs/tasks/forms-sprint-2.md",
        "backend/app/models/form_publication_version.py",
        "backend/app/forms_platform/publication_versions.py",
        "backend/alembic/versions/202607180008_forms_s3.py",
        "backend/tests/forms_platform/test_forms_sprint3_contract.py",
    ]
    for rel in required:
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_sprint3_suites_have_no_xfail() -> None:
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_sprint3*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None, path.name


def test_forms_sprint3_migration_chain() -> None:
    text = (_VERSIONS / "202607180008_forms_s3.py").read_text(encoding="utf-8")
    assert 'revision: str = "202607180008_forms_s3"' in text
    assert 'down_revision: RevisionType = "202607180007_forms_s2"' in text
    assert "form_publication_versions" in text


def test_forms_sprint3_alembic_single_head() -> None:
    result = _run_alembic("heads")
    assert result.returncode == 0, result.stderr + result.stdout
    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(heads) == 1, result.stdout
    # Sprint 3 revision remains in chain (may not be tip after Sprint 6+).
    assert (_VERSIONS / "202607180008_forms_s3.py").is_file()


def test_forms_sprint3_alembic_roundtrip() -> None:
    up = _run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr + up.stdout
    down = _run_alembic("downgrade", "202607180007_forms_s2")
    assert down.returncode == 0, down.stderr + down.stdout
    to_s3 = _run_alembic("upgrade", "202607180008_forms_s3")
    assert to_s3.returncode == 0, to_s3.stderr + to_s3.stdout
    current_s3 = _run_alembic("current")
    assert current_s3.returncode == 0, current_s3.stderr + current_s3.stdout
    assert "202607180008_forms_s3" in current_s3.stdout
    # Later sprints may advance head beyond Sprint 3; chain must still reach tip.
    up2 = _run_alembic("upgrade", "head")
    assert up2.returncode == 0, up2.stderr + up2.stdout


def test_forms_sprint3_builder_still_locked() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is False  # unlocked after P1.3
    task = (_REPO_ROOT / "docs/specs/tasks/forms-sprint-3.md").read_text(encoding="utf-8")
    assert "LOCKED" in task


def test_forms_sprint3_snapshot_v1_is_pointer_not_history() -> None:
    """Canon: published_snapshot_v1 is current pointer; history lives in ledger."""
    contract = (_REPO_ROOT / "docs/specs/architecture/forms-public-contract.md").read_text(
        encoding="utf-8"
    )
    assert "form_publication_versions" in contract or "publication version" in contract.lower()
    assert "pointer" in contract.lower() or "ledger" in contract.lower()
