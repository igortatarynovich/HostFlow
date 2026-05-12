"""Rules engine — candidate ``documents.*`` flags vs required/optional checklist."""

from __future__ import annotations

from backend.app.modules.documents.rules_engine import compute_candidate_checklist


def _minimal_advanced_ruleset() -> dict:
    return {
        "candidate": {
            "defaults": {
                "requiredTypes": ["identity_document"],
                "optionalTypes": [],
            },
            "overrides": [],
        },
        "vacancy": {"category_sets": {}, "additions": []},
        "expiring_soon_default_days": 30,
    }


def test_medical_flag_adds_medical_certificate_to_optional_not_required() -> None:
    rs = _minimal_advanced_ruleset()
    ctx = {
        "documents": {"medical": True},
        "vacancy": {"category": "non_driver"},
    }
    out = compute_candidate_checklist(ctx, rs)
    assert "medical_certificate" in out["optionalTypes"]
    assert "medical_certificate" not in out["requiredTypes"]
    assert "medical_certificate" in (out["debug"] or {}).get("added_by_candidate_flags", [])


def test_passport_flag_still_promotes_to_required() -> None:
    rs = _minimal_advanced_ruleset()
    ctx = {"documents": {"passport": True}}
    out = compute_candidate_checklist(ctx, rs)
    assert "passport" in out["requiredTypes"]
    assert "passport" in (out["debug"] or {}).get("added_by_candidate_flags", [])
