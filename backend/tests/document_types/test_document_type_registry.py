from __future__ import annotations

import pytest

from backend.app.document_types.registry import (
    build_legacy_to_canonical_map,
    canonical_codes,
    driver_ce_canonical_codes,
    is_canonical_code,
    is_runtime_alias,
    legacy_codes_for_canonical,
    normalize_input_doc_type,
    registry_version,
)


def test_registry_version_present() -> None:
    assert registry_version() == "1.1.0"


def test_driver_ce_canonical_codes() -> None:
    expected = {
        "passport",
        "national_identity_card",
        "residence_card",
        "visa",
        "driver_license",
        "driver_qualification_card",
        "tachograph_card",
        "medical_certificate",
        "psychological_certificate",
        "work_permit",
        "driver_attestation",
        "work_permit_decision",
        "temporary_residence_decision",
        "temporary_residence_and_work_decision",
        "eu_residence_registration",
    }
    assert expected <= driver_ce_canonical_codes()


def test_legacy_aliases_normalize_to_canonical() -> None:
    assert normalize_input_doc_type("tacho_card") == "tachograph_card"
    assert normalize_input_doc_type("psych_tests") == "psychological_certificate"
    assert normalize_input_doc_type("code95") == "driver_qualification_card"
    assert normalize_input_doc_type("national_id") == "national_identity_card"
    assert normalize_input_doc_type("decision") == "other"
    assert normalize_input_doc_type("voivodeship_decision") == "other"
    assert normalize_input_doc_type("driver_certificate") == "other"
    assert normalize_input_doc_type("additional_document") == "other"


def test_deprecated_canonical_codes_map_forward() -> None:
    assert normalize_input_doc_type("psychotest") == "psychological_certificate"
    assert normalize_input_doc_type("code_95") == "driver_qualification_card"
    assert normalize_input_doc_type("id_card") == "national_identity_card"


def test_canonical_codes_are_not_aliases() -> None:
    for code in ("passport", "driver_license", "psychological_certificate"):
        assert is_canonical_code(code)
        assert not is_runtime_alias(code)


def test_legacy_strings_are_aliases() -> None:
    assert is_runtime_alias("psych_tests")
    assert is_runtime_alias("tacho_card")


def test_legacy_codes_for_canonical() -> None:
    tacho_aliases = legacy_codes_for_canonical("tachograph_card")
    assert "tacho_card" in tacho_aliases

    psycho_aliases = legacy_codes_for_canonical("psychological_certificate")
    assert "psych_tests" in psycho_aliases


def test_all_canonical_codes_self_normalize() -> None:
    mapping = build_legacy_to_canonical_map()
    for code in canonical_codes():
        assert mapping.get(code) == code
        assert normalize_input_doc_type(code) == code
