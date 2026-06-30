"""M4: funnels API company-scoped CRUD gate (source-level contract tests)."""

from __future__ import annotations

from pathlib import Path


def test_funnels_api_requires_company_id_on_list() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "company_id: str = Query(..., min_length=1" in source
    assert "Funnel.company_id ==" in source
    assert "Funnel.module_key ==" in source


def test_funnels_api_create_sets_module_key_and_company() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "company_id: str = Field(..., min_length=1" in source
    assert "module_key=RECRUITMENT_MODULE_KEY" in source
    assert "_ensure_funnel_mutable" in source


def test_funnels_api_legacy_readonly_guard() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "Legacy tenant-wide funnels are read-only" in source
    assert "is_legacy_readonly" in source


def test_funnels_api_schema_allows_employee_type_constant() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "FUNNEL_TYPE_PATTERN" in source
    assert "pattern=FUNNEL_TYPE_PATTERN" in source
