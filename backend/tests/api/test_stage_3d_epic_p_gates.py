"""ADR-024 Epic P PR-4 — regression / Alembic / base-known CI gates."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_VERSIONS = _BACKEND_ROOT / "alembic" / "versions"

_EPIC_P_MIGRATIONS = (
    "202607180004_acq_3d",
    "202607180005_acq_3d_o",
    "202607180006_acq_3d_k",
)

_EPIC_P_CONTRACT_SUITES = (
    "backend/tests/api/test_stage_3d_outcome_attribution.py",
    "backend/tests/api/test_stage_3d_outcome_lifecycle.py",
    "backend/tests/api/test_stage_3d_kpi_aggregates.py",
    "backend/tests/api/test_stage_3d_epic_p_contract.py",
    "backend/tests/api/test_stage_3a_campaign_foundation.py",
    "backend/tests/api/test_stage_3b_form_intake_binding.py",
    "backend/tests/api/test_stage_3c_universal_submission_routing.py",
)

# Files introduced / owned by Epic P Stage 3D — must not add SPA /app literals.
_EPIC_P_CODE_GLOBS = (
    "backend/app/acquisition/result_attribution.py",
    "backend/app/acquisition/outcome_service.py",
    "backend/app/acquisition/kpi_aggregates.py",
    "backend/alembic/versions/202607180004_acq_3d.py",
    "backend/alembic/versions/202607180005_acq_3d_o.py",
    "backend/alembic/versions/202607180006_acq_3d_k.py",
)

# Fingerprints of integration base-known CI failures (NOT introduced by Epic P).
# Evidence: PR #31 CI on integration/release-product-a-b — failures in files outside Epic P.
_BASE_KNOWN_SPA_LITERAL_FILES = (
    "backend/app/modules/leads/schemas.py",
    "backend/app/services/communication_deliveries/questionnaire_email.py",
    "backend/app/services/recruitment_setup_readiness.py",
    "backend/app/services/search_workspace_service.py",
)

_BASE_KNOWN_DOCS_LINK_FILES = (
    "docs/specs/architecture/ADR-018-requirement-policy-evaluation-model.md",
    "docs/specs/architecture/ADR-023-recruitment-sales-module-separation.md",
    "docs/specs/tasks/intake-form-purpose-phase1-backend.md",
)


def _alembic_bin() -> str:
    for rel in (".venv312/bin/alembic", ".venv/bin/alembic"):
        candidate = _REPO_ROOT / rel
        if candidate.is_file():
            return str(candidate)
    return "alembic"


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    # Prefer host-local DB when compose hostname is unresolved.
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


def test_epic_p_regression_suite_modules_exist() -> None:
    for rel in _EPIC_P_CONTRACT_SUITES:
        path = _REPO_ROOT / rel
        assert path.is_file(), f"missing Epic P / Stage 3 contract suite: {rel}"


def test_epic_p_suites_have_no_xfail_markers() -> None:
    pattern = re.compile(r"@pytest\.mark\.xfail")
    for rel in _EPIC_P_CONTRACT_SUITES:
        if "stage_3a" in rel or "stage_3b" in rel or "stage_3c" in rel:
            continue
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert not pattern.search(text), f"xfail still present in {rel}"


def test_epic_p_code_introduces_no_spa_app_literals() -> None:
    needle = re.compile(r"[\"']/app/")
    for rel in _EPIC_P_CODE_GLOBS:
        path = _REPO_ROOT / rel
        assert path.is_file(), rel
        text = path.read_text(encoding="utf-8")
        assert not needle.search(text), f"Epic P file introduces SPA /app literal: {rel}"


def test_base_known_ci_failures_still_outside_epic_p_surface() -> None:
    """Document that known SPA/docs failures live on integration base paths, not Epic P."""
    for rel in _BASE_KNOWN_SPA_LITERAL_FILES:
        assert (_REPO_ROOT / rel).is_file(), rel
    for rel in _BASE_KNOWN_DOCS_LINK_FILES:
        assert (_REPO_ROOT / rel).is_file(), rel
    # Epic P owned code paths are disjoint from the known SPA offenders.
    epic = {Path(p).as_posix() for p in _EPIC_P_CODE_GLOBS}
    known = {Path(p).as_posix() for p in _BASE_KNOWN_SPA_LITERAL_FILES}
    assert epic.isdisjoint(known)


def test_epic_p_alembic_revision_chain_in_tree() -> None:
    files = {p.name: p for p in _VERSIONS.glob("20260718000*_acq_3d*.py")}
    assert "202607180004_acq_3d.py" in files
    assert "202607180005_acq_3d_o.py" in files
    assert "202607180006_acq_3d_k.py" in files

    text_004 = files["202607180004_acq_3d.py"].read_text(encoding="utf-8")
    text_005 = files["202607180005_acq_3d_o.py"].read_text(encoding="utf-8")
    text_006 = files["202607180006_acq_3d_k.py"].read_text(encoding="utf-8")
    assert 'revision: str = "202607180004_acq_3d"' in text_004
    assert 'down_revision' in text_004
    assert 'revision: str = "202607180005_acq_3d_o"' in text_005
    assert 'down_revision: RevisionType = "202607180004_acq_3d"' in text_005
    assert 'revision: str = "202607180006_acq_3d_k"' in text_006
    assert 'down_revision: RevisionType = "202607180005_acq_3d_o"' in text_006


def test_epic_p_alembic_single_head() -> None:
    result = _run_alembic("heads")
    assert result.returncode == 0, result.stderr
    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(heads) == 1, f"Expected single Alembic head, got: {heads!r}\n{result.stdout}"


@pytest.mark.asyncio
async def test_epic_p_alembic_pr3_downgrade_upgrade_roundtrip() -> None:
    """Downgrade PR-3 revision, then upgrade back to head; leave DB at head."""
    # Ensure we are at head first.
    up = _run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr + up.stdout

    down = _run_alembic("downgrade", "202607180005_acq_3d_o")
    assert down.returncode == 0, down.stderr + down.stdout

    # PR-3 tables must be gone after downgrade.
    from sqlalchemy import text

    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        spend = await session.execute(
            text("SELECT to_regclass('public.acq_flight_spend_entries')")
        )
        qual = await session.execute(
            text("SELECT to_regclass('public.acq_result_qualifications')")
        )
        assert spend.scalar() is None
        assert qual.scalar() is None

    up2 = _run_alembic("upgrade", "head")
    assert up2.returncode == 0, up2.stderr + up2.stdout

    async with async_session_maker() as session:
        spend = await session.execute(
            text("SELECT to_regclass('public.acq_flight_spend_entries')")
        )
        qual = await session.execute(
            text("SELECT to_regclass('public.acq_result_qualifications')")
        )
        assert spend.scalar() == "acq_flight_spend_entries"
        assert qual.scalar() == "acq_result_qualifications"

    current = _run_alembic("current")
    assert current.returncode == 0, current.stderr
    assert "202607180006_acq_3d_k" in current.stdout
