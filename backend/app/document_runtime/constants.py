"""Document Runtime Engine constants."""

from __future__ import annotations

from typing import Literal

DOCUMENT_RUNTIME_V1 = "document_runtime_v1"

WorkflowStatus = Literal[
    "missing",
    "uploaded",
    "pending_review",
    "approved",
    "rejected",
    "replaced",
    "superseded",
]

ExpiryStatus = Literal["valid", "expiring_soon", "expired", "no_expiry"]

RuntimeSignal = Literal[
    "missing",
    "pending_verification",
    "rejected",
    "expired",
    "expiring_soon",
    "missing_expiry",
]
