from __future__ import annotations

from datetime import date, timedelta

from backend.app.modules.documents.reminder_candidate_projection import project_reminder_candidates_from_packs


def test_reminder_candidates_from_gaps_and_expiring() -> None:
    packs = [
        {
            "code": "driver_pack",
            "label": "Driver Pack",
            "status": "gaps",
            "skeleton": False,
            "missing": ["driver_license"],
            "expired": ["code_95"],
            "missing_expiry": [],
            "expiring_soon": [
                {
                    "document_code": "tachograph_card",
                    "expires_on": (date.today() + timedelta(days=5)).isoformat(),
                    "days_left": 5,
                }
            ],
        },
        {
            "code": "client_pack",
            "label": "Client Pack",
            "status": "skeleton",
            "skeleton": True,
        },
    ]
    out = project_reminder_candidates_from_packs(packs, owner_type="employee", reference_date=date(2026, 5, 1))
    by_code = {row["document_code"]: row for row in out}

    assert by_code["driver_license"]["reason"] == "missing"
    assert by_code["driver_license"]["severity"] == "high"
    assert by_code["driver_license"]["owner_type"] == "employee"
    assert by_code["driver_license"]["source_pack"] == "driver_pack"
    assert by_code["driver_license"]["recipient_role"] == "hr"

    assert by_code["code_95"]["reason"] == "expired"
    assert by_code["code_95"]["severity"] == "critical"

    assert by_code["tachograph_card"]["reason"] == "expiring_soon"
    assert by_code["tachograph_card"]["severity"] == "high"
    assert by_code["tachograph_card"]["days_left"] == 5


def test_reminder_candidates_empty_when_all_valid() -> None:
    packs = [
        {
            "code": "employment_pack",
            "label": "Employment Pack",
            "status": "valid",
            "skeleton": False,
            "missing": [],
            "expired": [],
            "missing_expiry": [],
            "expiring_soon": [],
        }
    ]
    assert project_reminder_candidates_from_packs(packs) == []
