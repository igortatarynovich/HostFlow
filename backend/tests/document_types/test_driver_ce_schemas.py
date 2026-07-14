"""Tests for Driver CE DocumentTypeVersion schemas (ADR-018 PR 2A)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.app.document_types.schema_registry import (
    driver_ce_schema_bundle_version,
    get_driver_ce_schema_bundle,
    normalize_raw_to_document_data,
    validate_document_data,
)


def test_driver_ce_schema_bundle_version() -> None:
    assert driver_ce_schema_bundle_version() == "driver_ce.v1"


@pytest.mark.parametrize(
    "document_type",
    [
        "passport",
        "national_identity_card",
        "driver_license",
        "driver_qualification_card",
        "tachograph_card",
        "psychological_certificate",
        "medical_certificate",
        "visa",
        "residence_card",
        "driver_attestation",
    ],
)
def test_driver_ce_schema_bundle_exists(document_type: str) -> None:
    bundle = get_driver_ce_schema_bundle(document_type)
    assert bundle is not None
    assert bundle.version_code == "v1"
    assert bundle.json_schema.get("type") == "object"


def test_passport_schema_validates() -> None:
    future = (date.today() + timedelta(days=365)).isoformat()
    data = {
        "document_number": "AB1234567",
        "issuing_country": "PL",
        "nationality": "BY",
        "expiry_date": future,
    }
    ok, errors = validate_document_data("passport", data)
    assert ok is True
    assert errors == []


def test_passport_schema_rejects_missing_required() -> None:
    ok, errors = validate_document_data("passport", {"document_number": "X"})
    assert ok is False
    assert any("nationality" in err or "expiry_date" in err for err in errors)


def test_driver_license_conditional_code95_required() -> None:
    future = (date.today() + timedelta(days=365)).isoformat()
    data = {
        "document_number": "DL123",
        "issuing_country": "PL",
        "categories": ["CE"],
        "expiry_date": future,
    }
    ok, errors = validate_document_data("driver_license", data)
    assert ok is False
    assert any("code_95_valid_to" in err for err in errors)


def test_normalize_raw_to_document_data_maps_legacy_meta() -> None:
    raw = {
        "number": "P123",
        "country": "PL",
        "nationality": "UA",
        "expires_at": "2030-01-01",
    }
    data = normalize_raw_to_document_data("passport", raw)
    assert data["document_number"] == "P123"
    assert data["issuing_country"] == "PL"
    assert data["expiry_date"] == "2030-01-01"
