from __future__ import annotations

from pathlib import Path


def test_idor_regression_anchor() -> None:
    """Placeholder anchor for future IDOR matrix (candidate/document/signed URL)."""
    root = Path(__file__).resolve().parents[2]
    assert (root / "api" / "test_tenant_isolation.py").is_file()
