"""M4: funnels API company-scoped CRUD gate (source-level contract tests)."""

from __future__ import annotations

from backend.tests.test_support.repo_paths import read_repo_text


def test_funnels_api_list_allows_tenant_catalog_without_company() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "company_id: Optional[str] = Query(None" in source
    assert "Funnel.module_key ==" in source
    assert "Funnel.company_id.isnot(None)" in source
    assert "_module_catalog_funnels" in source
    assert "if acl is not None and not acl.company_ids:" in source
    assert "Funnel.company_id.in_(list(acl.company_ids))" not in source


def test_funnels_api_create_sets_module_key_and_company() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "company_id: Optional[str] = Field(default=None" in source
    assert "module_key=RECRUITMENT_MODULE_KEY" in source
    assert "_ensure_funnel_mutable" in source


def test_funnels_api_legacy_readonly_guard() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "Legacy tenant-wide funnels are read-only" in source
    assert "is_legacy_readonly" in source


def test_funnels_api_schema_allows_employee_type_constant() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "FUNNEL_TYPE_PATTERN" in source
    assert "pattern=FUNNEL_TYPE_PATTERN" in source
