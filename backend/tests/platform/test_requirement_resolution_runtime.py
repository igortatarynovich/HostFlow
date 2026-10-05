"""Recruitment Requirement Resolution runtime. HR is not an input."""

from __future__ import annotations

from datetime import date

from backend.app.reference.requirement_policy_consumer_parity import (
    r5_required_set,
    require_overlay_delta,
)
from backend.app.reference.requirement_resolution import (
    POLICY_ID,
    apply_resolution_to_required_set,
    requirements_named_by_documents,
    resolve_recruitment_requirements,
)
_CE = [
    {"requirement_code": "ce", "level": "REQUIRED"},
    {"requirement_code": "code95", "level": "REQUIRED"},
]


def _facts(**patch: object) -> dict:
    facts = {
        "citizenship": "UA",
        "stay_basis": "karta_pobytu",
        "licence_issuing_country": None,
        "licence_categories": [],
        "code95_presence": None,
        "tachograph_presence": True,
        "adr_presence": True,
        "medical_presence": True,
    }
    facts.update(patch)
    return facts


def test_facts_do_not_name_a_requirement_or_a_document() -> None:
    rows = resolve_recruitment_requirements([], _facts(), [])
    assert rows == []
    assert apply_resolution_to_required_set([], rows) == []


def test_unknown_country_is_needs_input_and_asks_no_file() -> None:
    rows = resolve_recruitment_requirements(_CE, _facts(), [], today=date(2026, 10, 5))
    assert [row["progress"] for row in rows] == ["needs_input", "needs_input"]
    assert rows[0]["policy_id"] == POLICY_ID
    assert apply_resolution_to_required_set(["driver_license", "code95", "visa"], rows) == ["visa"]


def test_shared_and_separate_shapes_and_candidate_evidence() -> None:
    shared = resolve_recruitment_requirements(
        _CE,
        _facts(licence_issuing_country="PL", licence_categories=["CE"]),
        [],
    )
    assert shared[0]["evidence_variant"] == "combined_eu_license"
    assert shared[0]["progress"] == "needs_evidence"
    assert apply_resolution_to_required_set(["driver_license", "code95"], shared) == ["driver_license"]

    separate = resolve_recruitment_requirements(
        _CE,
        _facts(licence_issuing_country="BY", licence_categories=["CE"], code95_presence=True),
        [],
    )
    assert separate[1]["evidence_variant"] == "separate_license_and_code95"
    assert apply_resolution_to_required_set(["driver_license", "code95"], separate) == [
        "driver_license",
        "driver_qualification_card",
    ]

    approved = resolve_recruitment_requirements(
        _CE,
        _facts(licence_issuing_country="PL", licence_categories=["CE"]),
        [
            {
                "requirement_code": "ce",
                "evidence_variant_code": "combined_eu_license",
                "status": "approved",
                "document_ids": ["doc-1"],
            },
            {
                "requirement_code": "code95",
                "evidence_variant_code": "combined_eu_license",
                "status": "pending_review",
                "document_ids": ["doc-1"],
            },
        ],
    )
    assert approved[0]["progress"] == "satisfied"
    assert approved[1]["progress"] == "under_review"
    assert apply_resolution_to_required_set(["driver_license", "code95"], approved) == []


def test_blocking_entitlement_asks_no_ce_file() -> None:
    rows = resolve_recruitment_requirements(
        [{"requirement_code": "ce", "level": "REQUIRED"}],
        _facts(licence_issuing_country="PL", licence_categories=["B"]),
        [],
    )
    assert rows[0]["progress"] == "blocking"
    assert rows[0]["document_codes"] == []


def test_r5_materializes_only_the_resolved_evidence() -> None:
    policy = r5_required_set(None, require_overlay_delta("driver_license"))
    assert "driver_license" in policy
    named = requirements_named_by_documents(policy)
    assert {"requirement_code": "ce", "level": "REQUIRED"} in named
    rows = resolve_recruitment_requirements(
        named,
        _facts(licence_issuing_country="PL", licence_categories=["CE"]),
        [],
    )
    materialized = apply_resolution_to_required_set(sorted(policy), rows)
    added = set(materialized) - set(policy)
    assert added <= {"driver_license", "driver_qualification_card"}
    assert "driver_license" in materialized
    assert "adr_certificate" not in added
    assert "passport" not in added
