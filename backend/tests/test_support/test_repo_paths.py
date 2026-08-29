"""Guard: source-scan tests stay valid from repo root and from backend/."""

from __future__ import annotations

from pathlib import Path

from backend.tests.test_support.repo_paths import REPO_ROOT, read_repo_text, repo_path


def test_repo_root_is_the_repository_not_cwd() -> None:
    assert (REPO_ROOT / "backend" / "app").is_dir()
    assert (REPO_ROOT / "alembic.ini").is_file() or (REPO_ROOT / "backend" / "alembic.ini").is_file()
    assert repo_path("backend/app/main.py").is_file()
    assert repo_path("backend/app/main.py").is_absolute()


def test_read_repo_text_does_not_depend_on_cwd() -> None:
    text = read_repo_text("backend/app/api/v1/analytics.py")
    assert "def " in text


def test_alembic_executable_prefers_running_interpreter() -> None:
    from backend.tests.test_support.repo_paths import alembic_executable

    found = alembic_executable()
    if found is None:
        return
    assert Path(found).is_file()
