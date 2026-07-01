from __future__ import annotations

from pathlib import Path

from backend.app.services.document_applicability_policy import derive_document_applicability_decision


def test_document_applicability_policy_keeps_legacy_behavior_for_driver_non_eu_pl() -> None:
    out = derive_document_applicability_decision(
        citizenship="UA",
        work_country="PL",
        role="driver",
        eu_countries={"PL", "DE"},
        oswiadczenie_countries={"UA", "GE"},
    )
    assert out.work_permit_type == "oswiadczenie"
    assert out.visa_required is True
    assert out.driver_attestation_required is True


def test_document_applicability_policy_keeps_legacy_behavior_for_eu_worker() -> None:
    out = derive_document_applicability_decision(
        citizenship="PL",
        work_country="PL",
        role="worker",
        eu_countries={"PL", "DE"},
        oswiadczenie_countries={"UA", "GE"},
    )
    assert out.work_permit_type is None
    assert out.visa_required is False
    assert out.driver_attestation_required is False


def test_document_applicability_policy_is_module_owned() -> None:
    src = Path("/opt/HostFlow/backend/app/services/document_applicability_policy.py").read_text(encoding="utf-8")
    assert "backend.app.reference" not in src
    assert "ReferenceServiceFacade" not in src

