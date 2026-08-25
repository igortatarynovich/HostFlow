"""C0.3 — retry policy driven by normalized reason codes (not error text)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Final

from backend.app.communications.delivery_errors import (
    REASON_RATE_LIMIT,
    is_retryable_reason,
)

DEFAULT_MAX_ATTEMPTS: Final = 5
DEFAULT_BASE_BACKOFF_SECONDS: Final = 30
DEFAULT_MAX_BACKOFF_SECONDS: Final = 3600


def compute_next_retry_at(
    *,
    reason_code: str,
    attempt_number: int,
    retry_after_seconds: int | None = None,
    now: datetime | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_backoff_seconds: int = DEFAULT_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: int = DEFAULT_MAX_BACKOFF_SECONDS,
) -> datetime | None:
    """Return next retry timestamp, or None if retry is not allowed / exhausted."""
    if not is_retryable_reason(reason_code):
        return None
    if attempt_number >= max_attempts:
        return None
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)

    if reason_code == REASON_RATE_LIMIT and retry_after_seconds is not None:
        delay = max(1, int(retry_after_seconds))
    else:
        # Exponential backoff: base * 2^(attempt-1)
        delay = min(
            max_backoff_seconds,
            base_backoff_seconds * (2 ** max(0, attempt_number - 1)),
        )
    return clock + timedelta(seconds=delay)


def retry_decision(
    *,
    reason_code: str,
    attempt_number: int,
    retry_after_seconds: int | None = None,
    manual: bool = False,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    """Structured retry decision for diagnostics / operator UI."""
    permanent = not is_retryable_reason(reason_code)
    exhausted = attempt_number >= max_attempts
    allowed = (manual or not permanent) and not exhausted and (
        manual or is_retryable_reason(reason_code)
    )
    # Manual retry may proceed even for some permanent? Spec: permanent failure does not auto-retry.
    # Manual retry is audited separately; still blocked for permanent unless operator override.
    if permanent and not manual:
        allowed = False
    if permanent and manual:
        # Manual retry of permanent is allowed but flagged (operator override).
        allowed = True
    next_at = None
    if allowed and not permanent:
        next_at = compute_next_retry_at(
            reason_code=reason_code,
            attempt_number=attempt_number,
            retry_after_seconds=retry_after_seconds,
            max_attempts=max_attempts,
        )
        if next_at is None and not manual:
            allowed = False
            exhausted = True
    return {
        "allowed": bool(allowed),
        "manual": bool(manual),
        "permanent_failure": permanent,
        "exhausted": exhausted,
        "max_attempts": max_attempts,
        "attempt_number": attempt_number,
        "reason_code": reason_code,
        "next_retry_at": next_at.isoformat() if next_at else None,
        "retry_after_seconds": retry_after_seconds,
    }
