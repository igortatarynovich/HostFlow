"""Trusted employment identity reads for Workforce (and other consumers)."""

from __future__ import annotations

from backend.app.services.employment_identity_read_adapter import (
    CONSUMER_CLIENT_FORM,
    CONSUMER_CONTRACT_GENERATION,
    CONSUMER_EXPORT,
    CONSUMER_HR_REVIEW_DISPLAY,
    CONSUMER_PAYROLL_PREP,
    CONSUMER_PERMIT_APPLICATION,
    CONSUMER_ZUS_PREPARATION,
    TrustedEmploymentIdentityRead,
    TrustedIdentityAccessError,
    get_trusted_employment_identity,
    get_trusted_employment_identity_for_employee,
)

__all__ = [
    "CONSUMER_CLIENT_FORM",
    "CONSUMER_CONTRACT_GENERATION",
    "CONSUMER_EXPORT",
    "CONSUMER_HR_REVIEW_DISPLAY",
    "CONSUMER_PAYROLL_PREP",
    "CONSUMER_PERMIT_APPLICATION",
    "CONSUMER_ZUS_PREPARATION",
    "TrustedEmploymentIdentityRead",
    "TrustedIdentityAccessError",
    "get_trusted_employment_identity",
    "get_trusted_employment_identity_for_employee",
]
