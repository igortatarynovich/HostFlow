"""C0.3 — normalized delivery error taxonomy (separate from raw provider payload)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

REASON_AUTHENTICATION_CONFIGURATION: Final = "authentication_configuration"
REASON_INVALID_RECIPIENT: Final = "invalid_recipient"
REASON_CONSENT_POLICY_DENIAL: Final = "consent_policy_denial"
REASON_RATE_LIMIT: Final = "rate_limit"
REASON_PROVIDER_UNAVAILABLE: Final = "provider_unavailable"
REASON_TEMPORARY_TRANSPORT_ERROR: Final = "temporary_transport_error"
REASON_PERMANENT_REJECTION: Final = "permanent_rejection"
REASON_CONTENT_REJECTED: Final = "content_rejected"
REASON_EXPIRED: Final = "expired"
REASON_UNKNOWN_PROVIDER_RESPONSE: Final = "unknown_provider_response"
REASON_CANCELLED: Final = "cancelled"
REASON_SEND_FAILED: Final = "send_failed"  # generic transport failure before classify

REASON_CODES: frozenset[str] = frozenset(
    {
        REASON_AUTHENTICATION_CONFIGURATION,
        REASON_INVALID_RECIPIENT,
        REASON_CONSENT_POLICY_DENIAL,
        REASON_RATE_LIMIT,
        REASON_PROVIDER_UNAVAILABLE,
        REASON_TEMPORARY_TRANSPORT_ERROR,
        REASON_PERMANENT_REJECTION,
        REASON_CONTENT_REJECTED,
        REASON_EXPIRED,
        REASON_UNKNOWN_PROVIDER_RESPONSE,
        REASON_CANCELLED,
        REASON_SEND_FAILED,
    }
)

# Map reason → default canonical terminal-ish status hint for delivery.
REASON_TO_STATUS: dict[str, str] = {
    REASON_AUTHENTICATION_CONFIGURATION: "failed",
    REASON_INVALID_RECIPIENT: "undeliverable",
    REASON_CONSENT_POLICY_DENIAL: "rejected",
    REASON_RATE_LIMIT: "failed",
    REASON_PROVIDER_UNAVAILABLE: "failed",
    REASON_TEMPORARY_TRANSPORT_ERROR: "failed",
    REASON_PERMANENT_REJECTION: "rejected",
    REASON_CONTENT_REJECTED: "rejected",
    REASON_EXPIRED: "expired",
    REASON_UNKNOWN_PROVIDER_RESPONSE: "failed",
    REASON_CANCELLED: "cancelled",
    REASON_SEND_FAILED: "failed",
}


@dataclass(frozen=True, slots=True)
class NormalizedDeliveryError:
    reason_code: str
    retryable: bool
    provider_status: str | None = None
    provider_code: str | None = None
    safe_message: str | None = None
    retry_after_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason_code": self.reason_code,
            "retryable": self.retryable,
            "provider_status": self.provider_status,
            "provider_code": self.provider_code,
            "safe_message": self.safe_message,
            "retry_after_seconds": self.retry_after_seconds,
        }


_PERMANENT = frozenset(
    {
        REASON_AUTHENTICATION_CONFIGURATION,
        REASON_INVALID_RECIPIENT,
        REASON_CONSENT_POLICY_DENIAL,
        REASON_PERMANENT_REJECTION,
        REASON_CONTENT_REJECTED,
        REASON_EXPIRED,
        REASON_CANCELLED,
    }
)

_TEMPORARY = frozenset(
    {
        REASON_RATE_LIMIT,
        REASON_PROVIDER_UNAVAILABLE,
        REASON_TEMPORARY_TRANSPORT_ERROR,
        REASON_SEND_FAILED,
    }
)


def is_retryable_reason(reason_code: str) -> bool:
    code = str(reason_code or "").strip().lower()
    if code in _PERMANENT:
        return False
    if code in _TEMPORARY:
        return True
    return code == REASON_UNKNOWN_PROVIDER_RESPONSE


def normalize_delivery_error(
    *,
    reason_code: str | None = None,
    provider_status: str | None = None,
    provider_code: str | None = None,
    raw_message: str | None = None,
    retry_after_seconds: int | None = None,
) -> NormalizedDeliveryError:
    code = str(reason_code or "").strip().lower()
    if code not in REASON_CODES:
        code = _infer_reason_from_provider(
            provider_status=provider_status,
            provider_code=provider_code,
            raw_message=raw_message,
        )
    safe = _safe_operator_message(code, raw_message=raw_message)
    retryable = is_retryable_reason(code)
    if code == REASON_RATE_LIMIT and retry_after_seconds is None:
        retry_after_seconds = 60
    return NormalizedDeliveryError(
        reason_code=code,
        retryable=retryable,
        provider_status=(str(provider_status).strip() if provider_status else None),
        provider_code=(str(provider_code).strip() if provider_code else None),
        safe_message=safe,
        retry_after_seconds=retry_after_seconds,
    )


def _infer_reason_from_provider(
    *,
    provider_status: str | None,
    provider_code: str | None,
    raw_message: str | None,
) -> str:
    blob = " ".join(
        x for x in (provider_status, provider_code, raw_message) if x
    ).lower()
    if not blob:
        return REASON_UNKNOWN_PROVIDER_RESPONSE
    if any(k in blob for k in ("auth", "credential", "api key", "forbidden", "401", "403")):
        return REASON_AUTHENTICATION_CONFIGURATION
    if any(k in blob for k in ("invalid recipient", "unknown user", "not found", "550", "mailbox")):
        return REASON_INVALID_RECIPIENT
    if any(k in blob for k in ("consent", "rodo", "opt-out", "unsubscribe", "policy")):
        return REASON_CONSENT_POLICY_DENIAL
    if any(k in blob for k in ("rate", "429", "throttle", "too many")):
        return REASON_RATE_LIMIT
    if any(k in blob for k in ("timeout", "temporar", "421", "450", "try again", "unavailable")):
        if "unavailable" in blob or "503" in blob:
            return REASON_PROVIDER_UNAVAILABLE
        return REASON_TEMPORARY_TRANSPORT_ERROR
    if any(k in blob for k in ("bounce", "554", "reject", "blocked")):
        return REASON_PERMANENT_REJECTION
    if any(k in blob for k in ("content", "spam", "virus", "mime")):
        return REASON_CONTENT_REJECTED
    if "expir" in blob:
        return REASON_EXPIRED
    if "cancel" in blob:
        return REASON_CANCELLED
    return REASON_UNKNOWN_PROVIDER_RESPONSE


def _safe_operator_message(reason_code: str, *, raw_message: str | None) -> str:
    labels = {
        REASON_AUTHENTICATION_CONFIGURATION: "Provider authentication or configuration failed",
        REASON_INVALID_RECIPIENT: "Recipient address is invalid or does not exist",
        REASON_CONSENT_POLICY_DENIAL: "Blocked by consent or communication policy",
        REASON_RATE_LIMIT: "Provider rate limit reached",
        REASON_PROVIDER_UNAVAILABLE: "Provider temporarily unavailable",
        REASON_TEMPORARY_TRANSPORT_ERROR: "Temporary transport error",
        REASON_PERMANENT_REJECTION: "Provider permanently rejected the message",
        REASON_CONTENT_REJECTED: "Message content rejected by provider",
        REASON_EXPIRED: "Delivery window expired",
        REASON_CANCELLED: "Delivery cancelled",
        REASON_SEND_FAILED: "Send failed",
        REASON_UNKNOWN_PROVIDER_RESPONSE: "Unknown provider response",
    }
    base = labels.get(reason_code, "Delivery failed")
    # Never leak raw stack traces; short safe snippet only.
    snippet = str(raw_message or "").strip().replace("\n", " ")[:120]
    if snippet and reason_code in {REASON_SEND_FAILED, REASON_UNKNOWN_PROVIDER_RESPONSE}:
        return f"{base}: {snippet}"
    return base
