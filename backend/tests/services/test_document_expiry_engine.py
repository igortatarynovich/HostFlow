from __future__ import annotations

from datetime import date

from backend.app.services.document_expiry_engine import (
    aggregate_document_expiry_states,
    coerce_expiry_date,
    evaluate_document_expiry,
    evaluate_expiry,
    owner_expiry_aggregate_to_dict,
)


def test_coerce_expiry_date_accepts_iso_string() -> None:
    assert coerce_expiry_date("2026-07-10T00:00:00Z") == date(2026, 7, 10)


def test_evaluate_expiry_marks_expired() -> None:
    result = evaluate_expiry(
        expires_on="2026-01-10",
        reference_date=date(2026, 1, 11),
        expiring_soon_days=30,
    )
    assert result is not None
    assert result.state == "expired"
    assert result.days_left == -1


def test_evaluate_expiry_marks_expiring_soon() -> None:
    result = evaluate_expiry(
        expires_on="2026-01-20",
        reference_date=date(2026, 1, 1),
        expiring_soon_days=30,
    )
    assert result is not None
    assert result.state == "expiring_soon"
    assert result.days_left == 19


def test_evaluate_expiry_marks_valid() -> None:
    result = evaluate_expiry(
        expires_on="2026-03-15",
        reference_date=date(2026, 1, 1),
        expiring_soon_days=30,
    )
    assert result is not None
    assert result.state == "valid"
    assert result.days_left == 73


def test_evaluate_document_expiry_missing_expiry_when_required() -> None:
    result = evaluate_document_expiry(
        expires_on=None,
        expiry_required=True,
        reference_date=date(2026, 1, 1),
    )
    assert result.state == "missing_expiry"
    assert result.expires_on is None
    assert result.days_left is None


def test_evaluate_document_expiry_valid_when_expiry_not_required() -> None:
    result = evaluate_document_expiry(
        expires_on=None,
        expiry_required=False,
        reference_date=date(2026, 1, 1),
    )
    assert result.state == "valid"


def test_aggregate_document_expiry_states_all_valid() -> None:
    aggregate = aggregate_document_expiry_states(
        [
            evaluate_document_expiry(expires_on="2026-12-01", reference_date=date(2026, 1, 1)),
            evaluate_document_expiry(expires_on="2026-11-01", reference_date=date(2026, 1, 1)),
        ]
    )
    payload = owner_expiry_aggregate_to_dict(aggregate)
    assert payload == {
        "all_documents_valid": True,
        "has_expiring_documents": False,
        "has_expired_documents": False,
        "has_missing_expiry": False,
    }


def test_aggregate_document_expiry_states_mixed() -> None:
    aggregate = aggregate_document_expiry_states(
        [
            evaluate_document_expiry(expires_on="2026-12-01", reference_date=date(2026, 1, 1)),
            evaluate_document_expiry(
                expires_on="2026-01-20",
                reference_date=date(2026, 1, 1),
                expiring_soon_days=30,
            ),
            evaluate_document_expiry(
                expires_on="2025-12-01",
                reference_date=date(2026, 1, 1),
            ),
            evaluate_document_expiry(expires_on=None, expiry_required=True),
        ]
    )
    payload = owner_expiry_aggregate_to_dict(aggregate)
    assert payload["all_documents_valid"] is False
    assert payload["has_expiring_documents"] is True
    assert payload["has_expired_documents"] is True
    assert payload["has_missing_expiry"] is True
