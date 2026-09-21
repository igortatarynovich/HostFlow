"""Candidate stage writes consume LI-1 existence, not funnel leftovers (HE-2)."""

from __future__ import annotations

from pathlib import Path

from backend.app.api.v1.candidates.helpers import _normalize_stage_to_code
from backend.app.reference.hiring_stage_authority import hiring_stage_exists

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_global_catalog_does_not_know_funnel_local_codes() -> None:
    assert _normalize_stage_to_code("skontaktowac__sie_pozniej") is None
    assert _normalize_stage_to_code("contacted") == "contacted"
    assert hiring_stage_exists("contacted")
    assert not hiring_stage_exists("skontaktowac__sie_pozniej")


def test_candidate_stage_write_does_not_resolve_tenant_funnel_codes() -> None:
    service = (_REPO_ROOT / "backend/app/api/v1/candidates/service.py").read_text(
        encoding="utf-8"
    )
    helpers = (_REPO_ROOT / "backend/app/api/v1/candidates/helpers.py").read_text(
        encoding="utf-8"
    )
    assert "resolve_writable_stage_code" in service
    assert "FunnelStage.code" not in helpers
    assert "resolve_hiring_stage_key" in helpers
    assert "_STAGE_INDEX" not in helpers
