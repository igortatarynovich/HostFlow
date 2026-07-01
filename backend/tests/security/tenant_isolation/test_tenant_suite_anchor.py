from __future__ import annotations

from pathlib import Path


def test_api_tenant_isolation_module_exists() -> None:
    """Anchor: cross-tenant scenarios live in tests/api (see README in this folder)."""
    p = Path(__file__).resolve().parents[2] / "api" / "test_tenant_isolation.py"
    assert p.is_file(), f"Expected tenant isolation tests at {p}"
