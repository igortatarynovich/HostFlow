"""Tests for DocumentData contract and evaluation input (ADR-018 PR 2A)."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from backend.app.document_hub.document_data_contract import (
    FORBIDDEN_EVALUATION_SOURCES,
    RequirementEvaluationInputContract,
    build_document_data_contract_from_hub_row,
)


def test_forbidden_evaluation_sources_documented() -> None:
    assert "meta.extracted_fields" in FORBIDDEN_EVALUATION_SOURCES
    assert "custom_name" in FORBIDDEN_EVALUATION_SOURCES


def test_build_document_data_contract_from_hub_row_passport() -> None:
    future = (date.today() + timedelta(days=400)).isoformat()
    doc = SimpleNamespace(
        id="doc-1",
        doc_type="passport",
        document_type_id="type-id",
        document_type_version_id="ver-id",
        candidate_id="cand-1",
        status=SimpleNamespace(value="approved"),
        expire_date=None,
        meta={
            "number": "P123456",
            "country": "PL",
            "nationality": "BY",
            "expires_at": future,
        },
    )
    contract = build_document_data_contract_from_hub_row(doc)
    assert contract.document_type_code == "passport"
    assert contract.is_approved is True
    assert contract.document_data["document_number"] == "P123456"
    assert contract.schema_valid is True
    assert contract.document_type_version_id == "ver-id"


def test_evaluation_input_contract_shape() -> None:
    contract = RequirementEvaluationInputContract(
        entity_type="candidate",
        entity_id="c-1",
        policy_ref="recruitment.driver_ce.pl/v1",
        target_stage="permit_ordered",
        evaluation_date=date.today(),
        person_facts={"citizenship": "BY"},
        documents=(),
    )
    assert contract.policy_ref.endswith("/v1")
