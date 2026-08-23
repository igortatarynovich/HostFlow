from __future__ import annotations

from datetime import date, timedelta

from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.modules.documents.pack_projection import project_document_packs, project_document_packs_from_expected
from backend.app.services.document_applicability_policy import derive_document_applicability_decision
from backend.app.services.document_ruleset import load_default_ruleset


RULESET = load_default_ruleset()


def _driver_ctx() -> dict:
    return {
        "citizenship": "PL",
        "work_country": "PL",
        "position_category": "driver",
        "vacancy": {"requires_driver_attestation": False},
    }


def _non_eu_ctx() -> dict:
    return {
        "citizenship": "UA",
        "work_country": "PL",
        "position_category": "driver",
        "stage": "recruitment",
    }


def test_driver_pack_missing_license() -> None:
    docs = [
        {
            "type": "code95",
            "status": "approved",
            "expires_at": (date.today() + timedelta(days=120)).isoformat(),
        }
    ]
    packs = project_document_packs(_driver_ctx(), RULESET, docs)
    driver = next(item for item in packs if item["code"] == "driver_pack")

    assert "driver_license" in driver["required"]
    assert "driver_license" in driver["missing"]
    assert "driver_license" in driver["gaps"]
    assert "driver_license" in driver["blockers"]
    assert (
        "driver_qualification_card" in driver["present"]
        or "code95" in driver["present"]
        or "code_95" in driver["present"]
    )
    assert driver["status"] == "gaps"


def test_legal_stay_pack_passport_expired() -> None:
    docs = [
        {
            "type": "passport",
            "status": "approved",
            "expires_at": (date.today() - timedelta(days=3)).isoformat(),
        }
    ]
    packs = project_document_packs(_non_eu_ctx(), RULESET, docs)
    legal = next(item for item in packs if item["code"] == "legal_stay_pack")

    assert "passport" in legal["present"]
    assert "passport" in legal["expired"]
    assert "passport" in legal["gaps"]
    assert legal["status"] == "gaps"


def test_employment_pack_all_valid() -> None:
    ctx = {"citizenship": "PL", "work_country": "PL", "stage": "onboarding"}
    docs = [
        {"type": "employment_contract", "status": "approved"},
        {"type": "civil_contract", "status": "approved"},
        {"type": "zus_zua", "status": "approved"},
        {"type": "zus_zza", "status": "approved"},
        {"type": "tax_declaration", "status": "approved"},
    ]
    packs = project_document_packs(ctx, RULESET, docs)
    employment = next(item for item in packs if item["code"] == "employment_pack")

    assert employment["status"] == "valid"
    assert employment["gaps"] == []
    assert employment["warnings"] == []
    assert employment["expiry"]["all_documents_valid"] is True


def test_pack_gap_projection_preserves_module_owned_policy_for_eu_worker() -> None:
    decision = derive_document_applicability_decision(
        citizenship="PL",
        work_country="PL",
        role="driver",
        eu_countries={"PL", "DE"},
        oswiadczenie_countries={"UA", "GE"},
    )
    assert decision.visa_required is False

    packs = project_document_packs(
        {"citizenship": "PL", "work_country": "PL", "position_category": "driver"},
        RULESET,
        [],
    )
    legal = next(item for item in packs if item["code"] == "legal_stay_pack")
    assert "work_permit" not in legal["required"]
    assert "visa" not in legal["required"]


def test_owner_summary_includes_packs() -> None:
    out = compute_owner_summary(_driver_ctx(), RULESET, [])
    assert "packs" in out
    assert any(item["code"] == "driver_pack" for item in out["packs"])
    assert any(item["code"] == "client_pack" and item["status"] == "skeleton" for item in out["packs"])


def test_owner_summary_candidate_without_documents_shows_pack_gaps() -> None:
    out = compute_owner_summary(_driver_ctx(), RULESET, [])
    driver = next(item for item in out["packs"] if item["code"] == "driver_pack")
    assert driver["status"] == "gaps"
    assert driver["missing"]
    assert "reminder_candidates" in out
    assert any(row["reason"] == "missing" for row in out["reminder_candidates"])


def test_project_from_expected_documents_uses_required_flags() -> None:
    expected = [
        {
            "document_code": "driver_license",
            "required": True,
            "expiry_rules": {"has_expiry": True, "renewal_window_days": 60},
        },
        {
            "document_code": "code_95",
            "required": False,
            "expiry_rules": {"has_expiry": True, "renewal_window_days": 45},
        },
    ]
    packs = project_document_packs_from_expected(
        ctx=_driver_ctx(),
        ruleset=RULESET,
        docs=[],
        expected_documents=expected,
    )
    driver = next(item for item in packs if item["code"] == "driver_pack")
    assert driver["required"] == ["driver_license"]
    assert driver["missing"] == ["driver_license"]
