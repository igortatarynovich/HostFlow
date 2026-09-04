"""Unit tests for mapping_applied_v1 fingerprint / stamp helpers."""

from __future__ import annotations

from backend.app.acquisition.mapping_applied_stamp import (
    MAPPING_APPLIED_V1_KEY,
    fingerprint_mapping_rules,
    stamp_mapping_applied_v1,
)


def test_fingerprint_order_insensitive() -> None:
    a = [{"source": "email", "target": "email"}, {"source": "phone", "target": "phone"}]
    b = [{"target": "phone", "source": "phone"}, {"target": "email", "source": "email"}]
    assert fingerprint_mapping_rules(a) == fingerprint_mapping_rules(b)


def test_stamp_mapping_applied_writes_key() -> None:
    norm: dict = {}
    stamp = stamp_mapping_applied_v1(
        norm,
        rules=[{"source": "email", "target": "email"}],
        source_id="11111111-1111-1111-1111-111111111111",
        rules_source="profile",
    )
    assert MAPPING_APPLIED_V1_KEY in norm
    assert stamp["rules_count"] == 1
    assert stamp["rules_fingerprint"]
    assert stamp["rules_source"] == "profile"
    assert stamp["executable_rules"][0]["source"] == "email"


def test_compose_applied_evidence_empty_without_stamp() -> None:
    from backend.app.acquisition.mapping_applied_stamp import (
        compose_applied_evidence,
        empty_applied_evidence,
    )

    assert compose_applied_evidence(
        lead_id="lead-1",
        normalized={"email": "anna@example.com"},
        current_rules=[{"source": "email", "target": "email"}],
    ) == empty_applied_evidence()


def test_compose_applied_evidence_sentences_and_drift() -> None:
    from backend.app.acquisition.mapping_applied_stamp import (
        compose_applied_evidence,
        stamp_mapping_applied_v1,
    )

    rules = [
        {
            "source": "email",
            "target": "email",
            "qualified_field_code": "recruitment.candidate.contacts.email",
        }
    ]
    normalized: dict = {"email": "anna@example.com"}
    stamp_mapping_applied_v1(
        normalized,
        rules=rules,
        source_id="src-1",
        rules_source="authority",
    )
    evidence = compose_applied_evidence(
        lead_id="lead-1",
        normalized=normalized,
        current_rules=rules,
        destinations=[
            {
                "code": "recruitment.candidate.contacts.email",
                "label": "Email",
                "aliases": ["email"],
                "options": [],
            }
        ],
    )
    assert evidence["present"] is True
    assert evidence["lead_id"] == "lead-1"
    assert evidence["drift"] is False
    assert evidence["sentences"]
    assert evidence["sentences"][0]["sentence"] == "Last application wrote Email = anna@example.com"

    drifted = compose_applied_evidence(
        lead_id="lead-1",
        normalized=normalized,
        current_rules=rules + [{"source": "phone", "target": "phone"}],
        destinations=[],
    )
    assert drifted["drift"] is True
