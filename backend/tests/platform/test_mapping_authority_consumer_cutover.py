"""MA-4 vocabulary cutover — leftover ``target`` is not a production write key."""

from __future__ import annotations

from backend.app.entity_profile.mapping_validation import validate_mapping_rules_for_profile
from backend.app.entity_profile.public_intake_draft_session import (
    build_candidate_payload_from_intake_state,
)
from backend.app.field_registry.canonical_facts import (
    apply_authority_rules_to_sources,
    write_canonical_fact,
)
from backend.app.field_registry.intake_mapping import (
    enrich_mapping_rule_for_storage,
    rule_write_qualified_code,
)
from backend.app.modules.leads.conversion_mapping import (
    apply_executable_intake_mapping,
    compact_executable_rules,
)


def test_enrich_does_not_mint_leftover_target() -> None:
    enriched = enrich_mapping_rule_for_storage(
        {
            "source": "phone_number",
            "qualified_field_code": "recruitment.candidate.contacts.phone",
        }
    )
    assert not str(enriched.get("target") or "").strip()
    assert rule_write_qualified_code(enriched) == "recruitment.candidate.contacts.phone"


def test_leftover_target_is_inferred_to_qualified_write() -> None:
    assert (
        rule_write_qualified_code({"source": "email", "target": "email"})
        == "recruitment.candidate.contacts.email"
    )


def test_canonical_facts_are_the_write_bag() -> None:
    normalized: dict = {}
    write_canonical_fact(
        normalized,
        "recruitment.candidate.contacts.phone",
        "+48111",
    )
    write_canonical_fact(
        normalized,
        "recruitment.candidate.personal.in_poland",
        True,
    )
    facts = normalized["canonical_facts_v1"]
    assert facts["recruitment.candidate.contacts.phone"] == "+48111"
    assert facts["recruitment.candidate.personal.in_poland"] is True
    assert normalized.get("phone") == "+48111"
    assert "in_poland" not in normalized


def test_authority_rules_write_qualified_facts_only() -> None:
    facts = apply_authority_rules_to_sources(
        {"contacts.phone": "+48111", "in_poland": True},
        [
            {
                "source": "contacts.phone",
                "qualified_field_code": "recruitment.candidate.contacts.phone",
            }
        ],
    )
    assert facts == {"recruitment.candidate.contacts.phone": "+48111"}


def test_conversion_ignores_leftover_flat_keys() -> None:
    mapped = apply_executable_intake_mapping(
        {"in_poland": True, "phone": "+48111", "first_name": "Jan"}
    )
    assert mapped.columns == {}
    assert mapped.extra == {}
    assert mapped.personal == {}


def test_conversion_consumes_canonical_facts_and_rules() -> None:
    mapped = apply_executable_intake_mapping(
        {
            "canonical_facts_v1": {
                "recruitment.candidate.contacts.phone": "+48111",
            },
            "field_answers": [{"name": "which_licence", "values": ["CE"]}],
            "mapping_applied_v1": {
                "executable_rules": [
                    {
                        "source": "which_licence",
                        "qualified_field_code": "recruitment.candidate.personal.residency_status",
                    }
                ]
            },
        }
    )
    assert mapped.columns.get("phone") == "+48111"
    assert mapped.personal.get("residency_status") == "CE"


def test_compact_rules_do_not_mint_normalized_target() -> None:
    rules = compact_executable_rules(
        [
            {
                "source": "phone",
                "qualified_field_code": "recruitment.candidate.contacts.phone",
                "target": "phone",
            }
        ]
    )
    assert len(rules) == 1
    assert rules[0]["qualified_field_code"] == "recruitment.candidate.contacts.phone"
    assert "normalized_target" not in rules[0]


def test_public_payload_ignores_leftover_buckets() -> None:
    payload = build_candidate_payload_from_intake_state(
        tenant_id="t",
        intake_state={
            "contacts": {"phone": "+48000", "email": "skip@example.com"},
            "personal": {"citizenship": "PL", "in_poland": True, "full_name": "Jan Nowak"},
        },
        vacancy_id=None,
        source="public_intake",
    )
    assert payload["first_name"] == "Candidate"
    assert payload["last_name"] == "Draft"
    assert payload.get("phone") is None
    assert payload.get("email") is None
    assert "citizenship" not in (payload.get("personal_data") or {})


def test_public_payload_consumes_canonical_facts() -> None:
    payload = build_candidate_payload_from_intake_state(
        tenant_id="t",
        intake_state={
            "contacts": {"phone": "+48000"},
            "presentation_values_v1": {
                "recruitment.candidate.contacts.phone": "+48111",
                "recruitment.candidate.first_name": "Jan",
                "recruitment.candidate.last_name": "Nowak",
            },
        },
        vacancy_id="vac-1",
        source="public_intake",
    )
    assert payload["phone"] == "+48111"
    assert payload["first_name"] == "Jan"
    assert payload["last_name"] == "Nowak"
    assert payload["vacancy_id"] == "vac-1"


def test_legacy_candidate_profile_does_not_accept_unscoped_rules() -> None:
    result = validate_mapping_rules_for_profile(
        [{"source": "phone", "target": "phone"}],
        allowed_qualified_codes=set(),
        entity_profile_code=None,
        resolution_source="legacy_candidate_profile",
    )
    assert result.accepted_rules == []
    assert result.rejected_rules
    assert "legacy_candidate_profile_unscoped_mapping_rejected" in result.warnings


def test_legacy_candidate_profile_consumes_qualified_allow_list() -> None:
    result = validate_mapping_rules_for_profile(
        [
            {"source": "phone", "target": "phone"},
            {"source": "hobby", "target": "hobby"},
        ],
        allowed_qualified_codes={"recruitment.candidate.contacts.phone"},
        entity_profile_code=None,
        resolution_source="legacy_candidate_profile",
    )
    assert [row["qualified_field_code"] for row in result.accepted_rules] == [
        "recruitment.candidate.contacts.phone"
    ]
    assert len(result.rejected_rules) == 1
