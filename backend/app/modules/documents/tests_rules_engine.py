from __future__ import annotations

from rules_engine import (
    compute_candidate_checklist,
    expiring_threshold_for,
    load_ruleset,
)


def test_scenarios():
    rs = load_ruleset("data/sample_ruleset.json")

    ua = {
        "citizenship": "UA",
        "residency_status": "no_residence_card",
        "vacancy": {"requires_driver_attestation": True},
    }
    out = compute_candidate_checklist(ua, rs)
    assert "national_id" in out["requiredTypes"]
    assert "visa" in out["requiredTypes"]

    eu = {
        "citizenship": "PL",
        "residency_status": "eu_citizen",
        "vacancy": {"requires_driver_attestation": False},
    }
    out = compute_candidate_checklist(eu, rs)
    assert "visa" not in out["requiredTypes"]
    assert expiring_threshold_for("national_id", rs) == 180
    assert expiring_threshold_for("code95", rs) == 45
    assert expiring_threshold_for("driver_certificate", rs) == 30  # default
