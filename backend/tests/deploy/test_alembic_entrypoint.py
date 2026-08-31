"""OL-2C: repo-root alembic.ini is the canonical entrypoint."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]


def test_canonical_entrypoint_guard_passes() -> None:
    script = _REPO / "scripts" / "deploy" / "check_alembic_entrypoint.py"
    out = subprocess.check_output(["python3", str(script)], text=True)
    assert "alembic.ini" in out
    assert "canonical" in out.lower()


def test_release_proof_refuses_missing_sha() -> None:
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env.pop("GIT_SHA", None)
    env.pop("GITHUB_SHA", None)
    env["DATABASE_URL"] = "postgresql+asyncpg://hostflow:hostflow@127.0.0.1:1/none"
    env["HOSTFLOW_PROOF_ALLOW_DIRTY"] = "1"
    proc = subprocess.run(
        ["bash", str(_REPO / "scripts" / "deploy" / "release-proof.sh")],
        cwd=_REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "GIT_SHA or GITHUB_SHA is required" in proc.stderr


def test_release_proof_refuses_sha_mismatch() -> None:
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["GIT_SHA"] = "0" * 40
    env["HOSTFLOW_PROOF_ALLOW_DIRTY"] = "1"
    env["DATABASE_URL"] = "postgresql+asyncpg://hostflow:hostflow@127.0.0.1:1/none"
    proc = subprocess.run(
        ["bash", str(_REPO / "scripts" / "deploy" / "release-proof.sh")],
        cwd=_REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "does not match HEAD" in proc.stderr
