"""Candidate stage writes must accept tenant funnel codes, not only stages.py."""

from __future__ import annotations

from pathlib import Path

from backend.app.api.v1.candidates.helpers import _normalize_stage_to_code


def test_global_catalog_does_not_know_funnel_local_codes() -> None:
    assert _normalize_stage_to_code("skontaktowac__sie_pozniej") is None
    assert _normalize_stage_to_code("contacted") == "contacted"


def test_candidate_stage_write_resolves_tenant_funnel_codes() -> None:
    service = Path("backend/app/api/v1/candidates/service.py").read_text(encoding="utf-8")
    helpers = Path("backend/app/api/v1/candidates/helpers.py").read_text(encoding="utf-8")
    assert "resolve_writable_stage_code" in service
    assert "FunnelStage.code" in helpers
    assert "Funnel.tenant_id == str(tenant_id)" in helpers
    assert "_STAGE_INDEX" not in helpers
