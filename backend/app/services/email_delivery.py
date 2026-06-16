from __future__ import annotations

import os


def is_email_delivery_mock() -> bool:
    """Return True when email delivery should be suppressed (local/dev/test mode)."""
    mode = str(os.getenv("EMAIL_DELIVERY_MODE", "")).strip().lower()
    return mode in {"mock", "disabled", "off", "false", "0", "test"}
