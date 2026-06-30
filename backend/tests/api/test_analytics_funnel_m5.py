"""M5: /analytics/funnel company-scoped gate (source-level contract tests)."""

from __future__ import annotations

from pathlib import Path


def test_analytics_funnel_requires_company_or_legacy_flag() -> None:
    source = Path("backend/app/api/v1/analytics.py").read_text(encoding="utf-8")
    assert "legacy_tenant: bool = Query" in source
    assert "pipeline_type: str = Query" in source
    assert "build_recruitment_funnel_analytics" in source


def test_analytics_funnel_service_binds_active_funnel() -> None:
    source = Path("backend/app/services/recruitment_funnel_analytics.py").read_text(encoding="utf-8")
    assert "Candidate.funnel_id == funnel.id" in source
    assert "Lead.funnel_id == funnel.id" in source
    assert "code not in allowed_codes" in source
    assert "record_recruitment_funnel_analytics" in source


def test_analytics_funnel_metrics_track_pipeline_scope() -> None:
    source = Path("backend/app/services/recruitment_funnel_metrics.py").read_text(encoding="utf-8")
    assert "record_recruitment_funnel_analytics" in source
    assert "analytics_by_pipeline" in source
