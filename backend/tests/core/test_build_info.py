"""OL-2A C-3: process identity comes from the environment, not from .git."""

from __future__ import annotations

import os

from backend.app.core.build_info import read_build_info


def test_read_build_info_uses_baked_env(monkeypatch) -> None:
    monkeypatch.setenv("HOSTFLOW_REVISION", "abc123def456")
    monkeypatch.setenv("HOSTFLOW_VERSION", "release/v0.1.0")
    monkeypatch.setenv("HOSTFLOW_BUILT_AT", "2026-08-31T10:00:00Z")
    info = read_build_info()
    assert info["revision"] == "abc123def456"
    assert info["version"] == "release/v0.1.0"
    assert info["built_at"] == "2026-08-31T10:00:00Z"


def test_read_build_info_unknown_when_unset(monkeypatch) -> None:
    for key in (
        "HOSTFLOW_REVISION",
        "HOSTFLOW_VERSION",
        "HOSTFLOW_BUILT_AT",
        "GIT_SHA",
        "GIT_REF",
        "BUILD_TIME",
    ):
        monkeypatch.delenv(key, raising=False)
    info = read_build_info()
    assert info["revision"] == "unknown"
    assert info["version"] == "unknown"
    assert info["built_at"] == "unknown"


def test_read_build_info_does_not_consult_git(monkeypatch) -> None:
    monkeypatch.setenv("HOSTFLOW_REVISION", "from-env")
    monkeypatch.delenv("HOSTFLOW_VERSION", raising=False)
    monkeypatch.delenv("HOSTFLOW_BUILT_AT", raising=False)
    monkeypatch.delenv("GIT_SHA", raising=False)
    # A dirty or different checkout must not leak into the answer.
    monkeypatch.setenv("GIT_DIR", "/nonexistent")
    info = read_build_info()
    assert info["revision"] == "from-env"
    assert os.getenv("GIT_DIR") == "/nonexistent"
