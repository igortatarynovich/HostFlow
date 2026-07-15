"""Integration tests for RequirementEvaluationService matching (PR 2B-2)."""

from __future__ import annotations

from datetime import date

import pytest

from backend.app.document_hub.document_data_contract import DocumentDataContract, DocumentEntityLink
from backend.app.requirement_rules.evaluation.result_contract import (
    RequirementApplicability,
    RequirementEvaluationStatus,
)
from backend.app.requirement_rules.evaluation.service import (
    RequirementEvaluationRunInput,
    evaluate_requirements,
)
from backend.app.requirement_rules.requirement_rule_contract import PersonContext

POLICY = "recruitment.driver_ce.pl/v1"
ENTITY_ID = "candidate-test-1"


def _doc(
    document_type_code: str,
    *,
    document_id: str | None = None,
    review_status: str = "approved",
    valid_to: date | None = date(2030, 6, 1),
    schema_valid: bool = True,
    document_data: dict | None = None,
) -> DocumentDataContract:
    return DocumentDataContract(
        document_id=document_id or f"doc-{document_type_code}",
        document_type_code=document_type_code,
        document_type_id=None,
        document_type_version_id=f"{document_type_code}.v1",
        document_data=dict(document_data or {}),
        review_status=review_status,
        valid_from=date(2020, 1, 1),
        valid_to=valid_to,
        issuing_country="PL",
        schema_valid=schema_valid,
        schema_errors=(),
        entity_links=(DocumentEntityLink(owner_type="candidate", owner_id=ENTITY_ID),),
        lifecycle_status="active",
    )


def _run(
    *,
    citizenship: str | None,
    documents: tuple[DocumentDataContract, ...] = (),
    process_states: dict[str, str] | None = None,
    target_stage: str = "docs_received",
    international_haulage: bool = False,
    community_licence_carrier: bool = False,
) -> object:
    return evaluate_requirements(
        RequirementEvaluationRunInput(
            entity_type="candidate",
            entity_id=ENTITY_ID,
            policy_ref=POLICY,
            target_stage=target_stage,
            evaluation_date=date(2026, 7, 13),
            person=PersonContext(
                citizenship=citizenship,
                international_haulage=international_haulage,
                community_licence_carrier=community_licence_carrier,
            ),
            documents=documents,
            process_states=process_states or {},
        )
    )


def _row(result, requirement_code: str):
    for row in result.requirements:
        if row.requirement_code == requirement_code:
            return row
    raise AssertionError(f"requirement not found: {requirement_code}")


def test_passport_closes_identity() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "passport",
                document_data={
                    "document_number": "AB123456",
                    "issuing_country": "BY",
                    "nationality": "BY",
                    "expiry_date": "2030-06-01",
                },
            ),
        ),
    )
    row = _row(result, "identity_document")
    assert row.status == RequirementEvaluationStatus.fulfilled
    assert row.matched_alternative == "approved_passport"


def test_eu_citizenship_closes_labor_market_without_work_permit() -> None:
    result = _run(citizenship="de", target_stage="ready_for_hire")
    labor = _row(result, "labor_market_access")
    work_process = _row(result, "work_authorization_process")
    assert labor.status == RequirementEvaluationStatus.fulfilled
    assert labor.matched_alternative == "free_movement_labor_access"
    assert work_process.status == RequirementEvaluationStatus.not_applicable


def test_third_country_visa_closes_legal_stay_not_labor_market() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "visa",
                document_data={
                    "document_number": "V123",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                },
            ),
        ),
        target_stage="permit_ordered",
    )
    legal = _row(result, "legal_stay_confirmation")
    labor = _row(result, "labor_market_access")
    assert legal.status == RequirementEvaluationStatus.fulfilled
    assert labor.status in {
        RequirementEvaluationStatus.missing,
        RequirementEvaluationStatus.unresolved,
    }


def test_residence_card_without_labor_access_leaves_labor_unresolved() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "residence_card",
                document_data={
                    "document_number": "RC123",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                },
            ),
        ),
        target_stage="ready_for_hire",
    )
    legal = _row(result, "legal_stay_confirmation")
    labor = _row(result, "labor_market_access")
    assert legal.status == RequirementEvaluationStatus.fulfilled
    assert labor.status == RequirementEvaluationStatus.unresolved


def test_ce_licence_without_code95_closes_entitlement_not_qualification() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "driver_license",
                document_data={
                    "document_number": "DL1",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                    "categories": ["CE"],
                },
            ),
        ),
    )
    entitlement = _row(result, "driver_entitlement")
    qualification = _row(result, "professional_qualification")
    assert entitlement.status == RequirementEvaluationStatus.fulfilled
    assert qualification.status == RequirementEvaluationStatus.missing


def test_ce_licence_with_valid_code95_closes_both_requirements() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "driver_license",
                document_id="doc-licence-code95",
                document_data={
                    "document_number": "DL1",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                    "categories": ["CE"],
                    "code_95_valid_to": "2030-06-01",
                },
            ),
        ),
    )
    entitlement = _row(result, "driver_entitlement")
    qualification = _row(result, "professional_qualification")
    assert entitlement.status == RequirementEvaluationStatus.fulfilled
    assert qualification.status == RequirementEvaluationStatus.fulfilled
    assert entitlement.matched_documents[0].document_id == qualification.matched_documents[0].document_id
    assert entitlement.matched_documents[0].match_role != qualification.matched_documents[0].match_role


def test_expired_code95_gives_qualification_expired() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "driver_license",
                document_data={
                    "document_number": "DL1",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                    "categories": ["CE"],
                    "code_95_valid_to": "2020-01-01",
                },
            ),
        ),
    )
    entitlement = _row(result, "driver_entitlement")
    qualification = _row(result, "professional_qualification")
    assert entitlement.status == RequirementEvaluationStatus.fulfilled
    assert qualification.status == RequirementEvaluationStatus.expired


def test_separate_licence_and_qualification_card_closes_composite_path() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "driver_license",
                document_id="doc-licence",
                document_data={
                    "document_number": "DL1",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                    "categories": ["CE"],
                },
            ),
            _doc(
                "driver_qualification_card",
                document_id="doc-code95",
                document_data={
                    "document_number": "Q1",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                },
            ),
        ),
    )
    entitlement = _row(result, "driver_entitlement")
    qualification = _row(result, "professional_qualification")
    assert entitlement.status == RequirementEvaluationStatus.fulfilled
    assert qualification.status == RequirementEvaluationStatus.fulfilled
    assert entitlement.matched_documents[0].document_id == "doc-licence"
    assert qualification.matched_documents[0].document_id == "doc-code95"


def test_driver_attestation_submitted_is_process_pending() -> None:
    result = _run(
        citizenship="by",
        process_states={"driver_attestation": "application_submitted"},
        target_stage="ready_for_dispatch",
        international_haulage=True,
        community_licence_carrier=True,
    )
    row = _row(result, "driver_attestation")
    assert row.status == RequirementEvaluationStatus.process_pending


def test_driver_attestation_issued_closes_requirement() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "driver_attestation",
                document_data={
                    "document_number": "AT1",
                    "issuing_country": "PL",
                    "valid_to": "2030-06-01",
                },
                valid_to=date(2030, 6, 1),
            ),
        ),
        target_stage="ready_for_dispatch",
        international_haulage=True,
        community_licence_carrier=True,
    )
    row = _row(result, "driver_attestation")
    assert row.status == RequirementEvaluationStatus.fulfilled


def test_excluded_alternative_is_not_missing() -> None:
    result = _run(
        citizenship="by",
        documents=(
            _doc(
                "visa",
                document_data={
                    "document_number": "V123",
                    "issuing_country": "PL",
                    "expiry_date": "2030-06-01",
                },
            ),
        ),
        target_stage="permit_ordered",
    )
    legal = _row(result, "legal_stay_confirmation")
    assert legal.status == RequirementEvaluationStatus.fulfilled
    excluded_codes = {alt.alternative_code for alt in legal.excluded_alternatives}
    assert "approved_residence_card" in excluded_codes
    assert legal.status != RequirementEvaluationStatus.missing


def test_unknown_citizenship_is_unresolved() -> None:
    result = _run(citizenship=None, target_stage="ready_for_hire")
    labor = _row(result, "labor_market_access")
    assert labor.applicability == RequirementApplicability.unresolved
    assert labor.status == RequirementEvaluationStatus.unresolved


def test_input_document_order_does_not_change_result() -> None:
    docs_a = (
        _doc("passport", document_id="doc-a", document_data={"document_number": "A1", "issuing_country": "BY", "nationality": "BY", "expiry_date": "2030-06-01"}),
        _doc("driver_license", document_id="doc-b", document_data={"document_number": "DL1", "issuing_country": "PL", "expiry_date": "2030-06-01", "categories": ["CE"], "code_95_valid_to": "2030-06-01"}),
    )
    docs_b = (docs_a[1], docs_a[0])
    result_a = _run(citizenship="by", documents=docs_a)
    result_b = _run(citizenship="by", documents=docs_b)
    assert result_a.to_dict()["requirements"] == result_b.to_dict()["requirements"]


def test_same_fingerprint_produces_same_result() -> None:
    docs = (
        _doc("passport", document_data={"document_number": "A1", "issuing_country": "BY", "nationality": "BY", "expiry_date": "2030-06-01"}),
    )
    inp = RequirementEvaluationRunInput(
        entity_type="candidate",
        entity_id=ENTITY_ID,
        policy_ref=POLICY,
        target_stage="docs_received",
        evaluation_date=date(2026, 7, 13),
        person=PersonContext(citizenship="by"),
        documents=docs,
    )
    result1 = evaluate_requirements(inp)
    result2 = evaluate_requirements(inp)
    assert result1.input_fingerprint == result2.input_fingerprint
    assert result1.to_dict()["requirements"] == result2.to_dict()["requirements"]