"""Unit tests for calculated HR verification plan."""

from __future__ import annotations

from backend.app.services.hr_verification_plan import (
    STEP_LEGAL_STAY,
    STEP_PROFESSIONAL,
    TIER_HARD_BLOCKER,
    TIER_RECOMMENDED,
    TIER_REQUIRED,
    _classify_requirement_tier,
    _classify_slot,
    _is_eu_citizen,
    _is_requirement_waived,
    _recompute_plan_blocking,
    sync_verification_plan_with_enriched_docs,
    VERIFICATION_SLOT_DEFS,
)


def test_eu_vs_non_eu_citizenship_hint() -> None:
    assert _is_eu_citizen("PL") is True
    assert _is_eu_citizen("UA") is False


def test_non_eu_legal_stay_required_from_ruleset() -> None:
    slot = next(s for s in VERIFICATION_SLOT_DEFS if s.document_key == "Legal stay")
    level = _classify_slot(
        slot,
        required_types={"legal_stay", "passport"},
        optional_types=set(),
        journey={"steps": []},
        position_category="warehouse",
    )
    assert level == "required"


def test_eu_legal_stay_optional_when_only_in_optional_types() -> None:
    slot = next(s for s in VERIFICATION_SLOT_DEFS if s.document_key == "Legal stay")
    level = _classify_slot(
        slot,
        required_types={"passport"},
        optional_types={"legal_stay"},
        journey={"steps": []},
        position_category="office",
    )
    assert level == "optional"


def test_missing_required_field_blocks_plan() -> None:
    docs = [
        {
            "document_key": "Passport / ID",
            "requirement_tier": TIER_HARD_BLOCKER,
            "requirement_level": "required",
            "document_id": "d1",
            "verification_status": "verified",
            "fields_to_review": [
                {
                    "field_code": "citizenship",
                    "needs_manual_confirmation": True,
                    "confirmed": False,
                    "current_profile_values": {},
                }
            ],
            "reviewed_fields": {},
        }
    ]
    blocking, ok = _recompute_plan_blocking(docs)
    assert ok is False
    assert any("missing_required_field:Passport / ID:citizenship" in b for b in blocking)


def test_professional_slots_not_required_for_non_driver() -> None:
    slot = next(s for s in VERIFICATION_SLOT_DEFS if s.document_key == "Driver license")
    level = _classify_slot(
        slot,
        required_types={"passport", "identity_document"},
        optional_types=set(),
        journey={"steps": []},
        position_category="office",
    )
    assert level == "not_required"


def test_journey_forces_legal_stay_required() -> None:
    slot = next(s for s in VERIFICATION_SLOT_DEFS if s.document_key == "Legal stay")
    level = _classify_slot(
        slot,
        required_types=set(),
        optional_types=set(),
        journey={
            "steps": [
                {"code": "legal_stay", "status": "pending", "required_documents": ["legal_stay"]},
            ]
        },
        position_category="driver",
    )
    assert level == "required"


def test_passport_tier_is_hard_blocker() -> None:
    slot = next(s for s in VERIFICATION_SLOT_DEFS if s.document_key == "Passport / ID")
    tier = _classify_requirement_tier(
        slot, level="required", journey={"steps": []}, position_category="office"
    )
    assert tier == TIER_HARD_BLOCKER


def test_recommended_does_not_block_approve() -> None:
    docs = [
        {
            "document_key": "Medical",
            "requirement_tier": TIER_RECOMMENDED,
            "requirement_level": "optional",
            "document_id": None,
            "verification_status": "pending",
        }
    ]
    blocking, ok = _recompute_plan_blocking(docs)
    assert ok is True
    assert blocking == []


def test_waived_required_does_not_block() -> None:
    docs = [
        {
            "document_key": "Medical",
            "requirement_tier": TIER_REQUIRED,
            "document_id": None,
            "reviewed_fields": {"_requirement_waiver": {"reason": "Client accepted exception"}},
        }
    ]
    assert _is_requirement_waived(docs[0]) is True
    blocking, ok = _recompute_plan_blocking(docs)
    assert ok is True
    assert blocking == []


def test_sync_plan_clears_blocking_after_verify() -> None:
    plan = {
        "documents": [
            {
                "document_key": "Passport / ID",
                "requirement_tier": TIER_HARD_BLOCKER,
                "requirement_level": "required",
                "required": True,
                "document_id": "doc-1",
                "status": "uploaded",
            }
        ],
        "required_documents": [],
        "optional_documents": [],
        "blocking_reasons": ["document_not_confirmed:Passport / ID"],
        "can_complete_verification": False,
    }
    enriched = [
        {
            "document_key": "Passport / ID",
            "document_id": "doc-1",
            "verification_status": "verified",
            "status": "verified",
            "fields_to_review": [
                {
                    "field_code": "citizenship",
                    "label": "Citizenship",
                    "needs_manual_confirmation": False,
                    "confirmed": True,
                }
            ],
        }
    ]
    out = sync_verification_plan_with_enriched_docs(plan, enriched)
    assert out["can_complete_verification"] is True
    assert out["blocking_reasons"] == []


def test_passport_always_required() -> None:
    slot = next(s for s in VERIFICATION_SLOT_DEFS if s.document_key == "Passport / ID")
    level = _classify_slot(
        slot,
        required_types=set(),
        optional_types=set(),
        journey={"steps": []},
        position_category=None,
    )
    assert level == "required"
