"""HR inbox transfer summary helpers (PR17)."""

from __future__ import annotations

from backend.app.services.hr_inbox import _transfer_summary_from_snapshot


def test_transfer_summary_from_handoff_snapshot() -> None:
    snap = {
        "candidate": {
            "first_name": "Anna",
            "last_name": "Nowak",
            "email": "anna@example.com",
            "citizenship": "PL",
            "work_country": "PL",
            "position_category": "driver_ce",
        },
        "vacancy": {"title": "CE Driver"},
        "documents_count": 4,
    }
    out = _transfer_summary_from_snapshot(snap)
    assert out is not None
    assert out["first_name"] == "Anna"
    assert out["vacancy_title"] == "CE Driver"
    assert out["documents_count"] == 4
