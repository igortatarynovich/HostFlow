"""Deprecated compatibility wrapper.

Use `operational_risk_reference.py` as canonical source.
"""

from __future__ import annotations

from .operational_risk_reference import (
    IMPACT_CODES as OPERATIONAL_IMPACTS,
    NEXT_ACTION_CODES as OPERATIONAL_NEXT_ACTIONS,
    SEVERITY_CODES as OPERATIONAL_SEVERITIES,
    SIGNAL_CODES as OPERATIONAL_SIGNALS,
    STATUS_CODES as OPERATIONAL_STATUSES,
)
