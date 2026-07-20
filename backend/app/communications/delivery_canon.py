"""C0.3 — canonical delivery / message / attempt statuses (provider-agnostic)."""

from __future__ import annotations

from typing import Final

# Progress chain (delivery + attempt result).
STATUS_QUEUED: Final = "queued"
STATUS_ACCEPTED: Final = "accepted"
STATUS_SENT: Final = "sent"
STATUS_DELIVERED: Final = "delivered"

# Terminal negatives.
STATUS_FAILED: Final = "failed"
STATUS_REJECTED: Final = "rejected"
STATUS_BOUNCED: Final = "bounced"
STATUS_EXPIRED: Final = "expired"
STATUS_CANCELLED: Final = "cancelled"
STATUS_UNDELIVERABLE: Final = "undeliverable"

PROGRESS_ORDER: tuple[str, ...] = (
    STATUS_QUEUED,
    STATUS_ACCEPTED,
    STATUS_SENT,
    STATUS_DELIVERED,
)

TERMINAL_NEGATIVE: frozenset[str] = frozenset(
    {
        STATUS_FAILED,
        STATUS_REJECTED,
        STATUS_BOUNCED,
        STATUS_EXPIRED,
        STATUS_CANCELLED,
        STATUS_UNDELIVERABLE,
    }
)

TERMINAL_ALL: frozenset[str] = TERMINAL_NEGATIVE | {STATUS_DELIVERED}

# Message-level statuses kept for backward compat (read may still appear for inbound).
MESSAGE_STATUS_READ: Final = "read"

CANONICAL_STATUSES: frozenset[str] = frozenset(PROGRESS_ORDER) | TERMINAL_NEGATIVE | {
    MESSAGE_STATUS_READ
}

# Explicit allowlist — only these transitions are legal (plus identity).
# No backward progress; no delivered downgrade; no failed→queued rewind.
# Recovery: only `failed` may advance again via a new successful attempt.
# Other terminal negatives (cancelled/rejected/bounced/…) stay terminal.
# Delivered is terminal-success: never transition to a negative from it.
_PROGRESS_TO_TERMINAL: frozenset[tuple[str, str]] = frozenset(
    (src, neg)
    for src in (STATUS_QUEUED, STATUS_ACCEPTED, STATUS_SENT)
    for neg in TERMINAL_NEGATIVE
)
_FORWARD_PROGRESS: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_QUEUED, STATUS_ACCEPTED),
        (STATUS_QUEUED, STATUS_SENT),
        (STATUS_QUEUED, STATUS_DELIVERED),
        (STATUS_ACCEPTED, STATUS_SENT),
        (STATUS_ACCEPTED, STATUS_DELIVERED),
        (STATUS_SENT, STATUS_DELIVERED),
    }
)
_FAILED_RECOVERY: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_FAILED, STATUS_ACCEPTED),
        (STATUS_FAILED, STATUS_SENT),
        (STATUS_FAILED, STATUS_DELIVERED),
    }
)
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = (
    _FORWARD_PROGRESS
    | _PROGRESS_TO_TERMINAL
    | _FAILED_RECOVERY
    | frozenset((s, s) for s in CANONICAL_STATUSES)  # idempotent replay
)


def is_terminal(status: str) -> bool:
    return str(status or "").strip().lower() in TERMINAL_ALL


def is_terminal_negative(status: str) -> bool:
    return str(status or "").strip().lower() in TERMINAL_NEGATIVE


def progress_rank(status: str) -> int:
    key = str(status or "").strip().lower()
    try:
        return PROGRESS_ORDER.index(key)
    except ValueError:
        return -1


def can_transition(current: str, new: str) -> bool:
    """True only for explicitly allowed canonical transitions."""
    cur = str(current or "").strip().lower() or STATUS_QUEUED
    nxt = str(new or "").strip().lower()
    if cur not in CANONICAL_STATUSES or nxt not in CANONICAL_STATUSES:
        return False
    return (cur, nxt) in ALLOWED_TRANSITIONS


def normalize_canonical_status(value: str | None, *, default: str = STATUS_QUEUED) -> str:
    key = str(value or "").strip().lower()
    if key in CANONICAL_STATUSES:
        return key
    # Legacy aliases.
    aliases = {
        "undelivered": STATUS_UNDELIVERABLE,
        "unknown": STATUS_FAILED,
        "error": STATUS_FAILED,
        "success": STATUS_DELIVERED,
    }
    return aliases.get(key, default)
