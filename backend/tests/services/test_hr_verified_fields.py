"""HR verified fields SoT (PR4)."""

from __future__ import annotations

from backend.app.services.hr_verified_fields import (
    critical_fields_block_approval,
    summarize_critical,
)
from backend.app.services.hr_verified_field_catalog import CRITICAL_FIELD_CODES


def _field(code: str, status: str, **extra) -> dict:
    return {
        "field_code": code,
        "field_label": code,
        "status": status,
        "is_critical": code in CRITICAL_FIELD_CODES,
        **extra,
    }


def test_summarize_critical_blocks_when_pending() -> None:
    fields = [_field(c, "pending") for c in CRITICAL_FIELD_CODES]
    summary = summarize_critical(fields)
    assert summary["ready"] is False
    assert summary["critical_total"] == len(CRITICAL_FIELD_CODES)
    assert len(summary["pending_codes"]) == len(CRITICAL_FIELD_CODES)
    blocked, blockers = critical_fields_block_approval(fields)
    assert blocked is True
    assert blockers


def test_summarize_critical_ready_when_all_verified() -> None:
    fields = [_field(c, "verified", verified_value=f"v-{c}") for c in CRITICAL_FIELD_CODES]
    summary = summarize_critical(fields)
    assert summary["ready"] is True
    assert summary["critical_verified"] == len(CRITICAL_FIELD_CODES)
    blocked, _ = critical_fields_block_approval(fields)
    assert blocked is False


def test_summarize_critical_conflict_blocks() -> None:
    fields = [_field(c, "verified", verified_value="ok") for c in CRITICAL_FIELD_CODES]
    fields[0] = _field("full_name", "conflict", conflict_reason="mismatch")
    summary = summarize_critical(fields)
    assert summary["ready"] is False
    assert "full_name" in summary["conflict_codes"]


def test_override_status_counts_as_ready() -> None:
    fields = [_field(c, "overridden", verified_value=f"v-{c}") for c in CRITICAL_FIELD_CODES]
    summary = summarize_critical(fields)
    assert summary["ready"] is True
