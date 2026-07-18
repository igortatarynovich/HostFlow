"""Forms Sprint 1 — governance / regression gates."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_VERSIONS = _BACKEND_ROOT / "alembic" / "versions"

_FORMS_SURFACE = (
    "backend/app/forms_platform/",
    "backend/tests/forms_platform/",
    "docs/specs/architecture/forms-public-contract.md",
    "docs/specs/tasks/forms-sprint-1.md",
    "docs/forms/module-scope.md",
)
_REQUIRED_DOCS = (
    "docs/specs/tasks/forms-sprint-1.md",
    "docs/specs/architecture/forms-public-contract.md",
    "docs/forms/module-scope.md",
    "docs/specs/architecture/ADR-007-forms-platform-capability.md",
    "docs/specs/architecture/capability-contract.md",
    "docs/specs/architecture/capability-settings-manifest.md",
    "docs/specs/architecture/platform-capability-catalog.md",
)
_REQUIRED_CODE = (
    "backend/app/forms_platform/adapter.py",
    "backend/app/forms_platform/manifest.py",
    "backend/tests/forms_platform/test_forms_sprint1_contract.py",
)
_APP_LITERAL = re.compile(r"""['\"]/app/""")
_XFAIL = re.compile(r"@pytest\.mark\.xfail")
_IMPORT_FORBIDDEN = re.compile(
    r"^\s*(from|import)\s+.*(outcome_service|kpi_aggregates|result_attribution)",
    re.MULTILINE,
)


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


def test_forms_sprint1_docs_and_code_exist() -> None:
    for rel in _REQUIRED_DOCS + _REQUIRED_CODE:
        assert (_REPO_ROOT / rel).is_file(), f"missing {rel}"


def test_forms_sprint1_suites_have_no_xfail() -> None:
    suite_dir = _REPO_ROOT / "backend/tests/forms_platform"
    for path in suite_dir.glob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        assert _XFAIL.search(text) is None, path.name


def test_forms_sprint1_surface_has_no_spa_app_literals() -> None:
    offenders: list[str] = []
    for rel in _FORMS_SURFACE:
        path = _REPO_ROOT / rel
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = list(path.rglob("*"))
        else:
            continue
        for f in files:
            if not f.is_file() or f.suffix not in {".py", ".md", ".ts", ".tsx"}:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            if _APP_LITERAL.search(text):
                offenders.append(str(f.relative_to(_REPO_ROOT)))
    assert not offenders, f"SPA /app literals on Forms Sprint 1 surface: {offenders}"


def test_forms_sprint1_docs_lock_builder_and_unlock_infra() -> None:
    task = (_REPO_ROOT / "docs/specs/tasks/forms-sprint-1.md").read_text(encoding="utf-8")
    contract = (_REPO_ROOT / "docs/specs/architecture/forms-public-contract.md").read_text(
        encoding="utf-8"
    )
    assert "LOCKED" in task
    assert "Builder" in task
    assert "forms.public_contract.v1" in contract
    assert "forms.endpoint_adapter_v1" in contract
    assert "Forbidden" in contract


def test_forms_sprint1_adapter_does_not_import_outcome_or_kpi() -> None:
    adapter = (_REPO_ROOT / "backend/app/forms_platform/adapter.py").read_text(encoding="utf-8")
    assert _IMPORT_FORBIDDEN.search(adapter) is None
    assert "FORMS_PUBLIC_CONTRACT_ID" in adapter
    assert "from backend.app.acquisition" not in adapter


def test_forms_sprint1_manifest_builder_default_false() -> None:
    from backend.app.forms_platform.manifest import (
        FORMS_MANIFEST_KEYS,
        builder_is_locked_by_manifest,
        forms_manifest_document,
    )

    assert builder_is_locked_by_manifest() is True
    assert FORMS_MANIFEST_KEYS["forms.feature_flags.builder_enabled"]["default"] is False
    doc = forms_manifest_document()
    assert doc["capability_id"] == "forms"
    assert "forms.adapter.id" in doc["keys"]


def test_forms_sprint1_adds_no_new_migration() -> None:
    """Sprint 1 is governance/adapter only — no new revision files for this sprint."""
    forbidden = list(_VERSIONS.glob("*forms_sprint*")) + list(
        _VERSIONS.glob("*sprint1*")
    ) + list(_VERSIONS.glob("20260718*forms*"))
    assert forbidden == [], f"unexpected Forms Sprint 1 migrations: {forbidden}"


def test_forms_sprint1_alembic_single_head() -> None:
    result = _run_alembic("heads")
    assert result.returncode == 0, result.stderr + result.stdout
    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(heads) == 1, f"Expected single Alembic head, got: {heads!r}\n{result.stdout}"
