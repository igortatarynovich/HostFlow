"""Employment identity projection from verified fields (PR5)."""

from __future__ import annotations

from backend.app.services.employment_identity_projection import (
    PROJECTION_STATUS_COMPLETE,
    PROJECTION_STATUS_CONFLICTED,
    PROJECTION_STATUS_INCOMPLETE,
    PROJECTION_STATUS_STALE,
    build_employment_identity_projection,
)


def _vf(
    code: str,
    value: str,
    *,
    status: str = "verified",
    source_document_key: str | None = None,
) -> dict:
    return {
        "field_code": code,
        "field_label": code,
        "status": status,
        "verified_value": value,
        "source_document_key": source_document_key,
        "is_critical": False,
    }


def test_projection_incomplete_without_required() -> None:
    out = build_employment_identity_projection([])
    assert out["status"] == PROJECTION_STATUS_INCOMPLETE
    assert "legal_name" in out["missing_required"]
    assert out["ready_for_downstream"] is False


def test_projection_complete_from_verified_fields() -> None:
    fields = [
        _vf("full_name", "Jan Kowalski"),
        _vf("citizenship", "UA"),
        _vf("pesel", "90010112345", source_document_key="Red paper"),
        _vf("permit_type", "work_permit", source_document_key="Work permit"),
        _vf("document_expiry", "2030-01-01", source_document_key="Work permit"),
        _vf("exam_valid_until", "2027-06-01", source_document_key="Medical"),
        _vf("exam_valid_until", "2027-06-01", source_document_key="Psychological"),
    ]
    out = build_employment_identity_projection(fields)
    assert out["status"] == PROJECTION_STATUS_COMPLETE
    assert out["attributes"]["legal_name"] == "Jan Kowalski"
    assert out["attributes"]["medical_expiry"] == "2027-06-01"
    assert out["attributes"]["psychotests_expiry"] == "2027-06-01"
    assert out["ready_for_downstream"] is True


def test_projection_conflicted() -> None:
    fields = [
        _vf("full_name", "Jan Kowalski"),
        _vf("citizenship", "UA", status="conflict"),
    ]
    out = build_employment_identity_projection(fields)
    assert out["status"] == PROJECTION_STATUS_CONFLICTED
    assert "citizenship" in out["conflicts"]


def test_projection_stale_when_permit_expired() -> None:
    fields = [
        _vf("full_name", "Jan Kowalski"),
        _vf("citizenship", "PL"),
        _vf("document_expiry", "2020-01-01", source_document_key="Work permit"),
    ]
    out = build_employment_identity_projection(fields)
    assert out["status"] == PROJECTION_STATUS_STALE
    assert out["ready_for_downstream"] is True
