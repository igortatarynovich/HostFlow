"""H4 — /meta/stages pipeline_type=employee contract."""

from __future__ import annotations

from backend.tests.test_support.repo_paths import read_repo_text


def test_meta_stages_employee_pipeline_requires_company_id() -> None:
    source = read_repo_text("backend/app/api/v1/meta.py")
    assert 'detail="company_id is required for pipeline_type=employee"' in source


def test_meta_stages_employee_pipeline_uses_hr_pe_mapping_filter() -> None:
    source = read_repo_text("backend/app/api/v1/meta.py")
    assert "pe_maps_to_module" in source
    assert "pipeline_type != \"employee\"" in source
