from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, Optional, Sequence

ExpiryState = Literal["valid", "expiring_soon", "expired", "missing_expiry"]


@dataclass(frozen=True)
class ExpiryEvaluation:
    state: ExpiryState
    expires_on: Optional[date] = None
    days_left: Optional[int] = None


@dataclass(frozen=True)
class OwnerExpiryAggregate:
    all_documents_valid: bool
    has_expiring_documents: bool
    has_expired_documents: bool
    has_missing_expiry: bool


def coerce_expiry_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:10]).date()
    except Exception:
        return None


def evaluate_expiry(
    *,
    expires_on: Any,
    reference_date: Optional[date] = None,
    expiring_soon_days: int = 30,
) -> Optional[ExpiryEvaluation]:
    """Evaluate expiry when a date is present. Returns None when date is absent."""
    expiry_date = coerce_expiry_date(expires_on)
    if expiry_date is None:
        return None

    ref = reference_date or date.today()
    days_left = (expiry_date - ref).days
    threshold = max(0, int(expiring_soon_days))

    if days_left < 0:
        state: ExpiryState = "expired"
    elif days_left <= threshold:
        state = "expiring_soon"
    else:
        state = "valid"

    return ExpiryEvaluation(
        state=state,
        expires_on=expiry_date,
        days_left=days_left,
    )


def evaluate_document_expiry(
    *,
    expires_on: Any,
    expiry_required: bool = False,
    reference_date: Optional[date] = None,
    expiring_soon_days: int = 30,
) -> ExpiryEvaluation:
    """
    Canonical per-document expiry evaluation.

    When expiry is required but the date is missing, returns ``missing_expiry``.
    When expiry is not required and the date is missing, returns ``valid``.
    """
    evaluation = evaluate_expiry(
        expires_on=expires_on,
        reference_date=reference_date,
        expiring_soon_days=expiring_soon_days,
    )
    if evaluation is not None:
        return evaluation
    if expiry_required:
        return ExpiryEvaluation(state="missing_expiry")
    return ExpiryEvaluation(state="valid")


def aggregate_document_expiry_states(
    evaluations: Sequence[ExpiryEvaluation],
) -> OwnerExpiryAggregate:
    """Aggregate per-document expiry evaluations into owner-level flags."""
    has_expiring = any(item.state == "expiring_soon" for item in evaluations)
    has_expired = any(item.state == "expired" for item in evaluations)
    has_missing_expiry = any(item.state == "missing_expiry" for item in evaluations)
    all_valid = not has_expiring and not has_expired and not has_missing_expiry
    return OwnerExpiryAggregate(
        all_documents_valid=all_valid,
        has_expiring_documents=has_expiring,
        has_expired_documents=has_expired,
        has_missing_expiry=has_missing_expiry,
    )


def owner_expiry_aggregate_to_dict(aggregate: OwnerExpiryAggregate) -> dict[str, bool]:
    return {
        "all_documents_valid": aggregate.all_documents_valid,
        "has_expiring_documents": aggregate.has_expiring_documents,
        "has_expired_documents": aggregate.has_expired_documents,
        "has_missing_expiry": aggregate.has_missing_expiry,
    }
