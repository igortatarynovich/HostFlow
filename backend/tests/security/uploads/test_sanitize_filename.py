from __future__ import annotations

from backend.app.modules.documents.storage import sanitize_filename


def test_sanitize_filename_strips_unsafe_chars() -> None:
    out = sanitize_filename("evil/../name.pdf")
    assert "/" not in out
    assert sanitize_filename(None) == "document"


def test_sanitize_filename_preserves_known_double_extension() -> None:
    """Regression: os.path.splitext keeps last extension only (evil.pdf → .exe)."""
    name = sanitize_filename("report.pdf.exe")
    assert name.endswith(".exe")
