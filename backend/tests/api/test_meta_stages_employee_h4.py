"""H4 — /meta/stages pipeline_type=employee contract."""

from __future__ import annotations

from pathlib import Path


def test_meta_stages_employee_pipeline_requires_company_id() -> None:
    source = Path("backend/app/api/v1/meta.py").read_text(encoding="utf-8")
    assert 'detail="company_id is required for pipeline_type=employee"' in source


def test_meta_stages_employee_pipeline_uses_hr_pe_mapping_filter() -> None:
    source = Path("backend/app/api/v1/meta.py").read_text(encoding="utf-8")
    assert "pe_maps_to_module" in source
    assert "pipeline_type != \"employee\"" in source
