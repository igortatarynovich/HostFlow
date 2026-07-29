"""SSOT §0b — worker job tenant_id fail-closed helpers."""

from __future__ import annotations

import pytest

from backend.app.security.worker_job_context import (
    JobTenantRequiredError,
    parse_required_job_tenant_id,
)


def test_parse_required_job_tenant_id_ok() -> None:
    tid = parse_required_job_tenant_id(
        "11111111-1111-1111-1111-111111111111",
        job_name="automation_evaluate_trigger",
    )
    assert str(tid) == "11111111-1111-1111-1111-111111111111"


@pytest.mark.parametrize("raw", [None, "", "   ", "not-a-uuid"])
def test_parse_required_job_tenant_id_fail_closed(raw: str | None) -> None:
    with pytest.raises(JobTenantRequiredError):
        parse_required_job_tenant_id(raw, job_name="calendar_sync_ingest")
