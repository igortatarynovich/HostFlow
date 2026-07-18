"""Forms Sprint 6 — governance / Alembic gates."""

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


def test_forms_sprint6_docs_and_code_exist() -> None:
    for rel in (
        "docs/specs/tasks/forms-sprint-6.md",
        "docs/specs/tasks/forms-sprint-5.md",
        "backend/app/models/form_submission_envelope.py",
        "backend/app/forms_platform/submission_envelope.py",
        "backend/alembic/versions/202607180009_forms_s6.py",
        "backend/tests/forms_platform/test_forms_sprint6_contract.py",
    ):
        assert (_REPO_ROOT / rel).is_file(), rel


def test_forms_sprint6_migration_chain() -> None:
    text = (_VERSIONS / "202607180009_forms_s6.py").read_text(encoding="utf-8")
    assert 'revision: str = "202607180009_forms_s6"' in text
    assert 'down_revision: RevisionType = "202607180008_forms_s3"' in text
    assert "form_submission_envelopes" in text


def test_forms_sprint6_alembic_single_head() -> None:
    result = _run_alembic("heads")
    assert result.returncode == 0, result.stderr + result.stdout
    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(heads) == 1, result.stdout
    assert "202607180009_forms_s6" in result.stdout


def test_forms_sprint6_alembic_roundtrip() -> None:
    up = _run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr + up.stdout
    down = _run_alembic("downgrade", "202607180008_forms_s3")
    assert down.returncode == 0, down.stderr + down.stdout
    up2 = _run_alembic("upgrade", "head")
    assert up2.returncode == 0, up2.stderr + up2.stdout
    current = _run_alembic("current")
    assert "202607180009_forms_s6" in current.stdout


def test_forms_sprint6_no_xfail_builder_locked() -> None:
    from backend.app.forms_platform.manifest import builder_is_locked_by_manifest

    assert builder_is_locked_by_manifest() is False  # unlocked after P1.3
    for path in (_REPO_ROOT / "backend/tests/forms_platform").glob("test_forms_sprint6*.py"):
        assert _XFAIL.search(path.read_text(encoding="utf-8")) is None
    svc = (_REPO_ROOT / "backend/app/forms_platform/submission_envelope.py").read_text(
        encoding="utf-8"
    )
    assert "from backend.app.acquisition" not in svc
    assert "second intake" not in svc.lower()
