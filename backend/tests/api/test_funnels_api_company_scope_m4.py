"""M4: funnels API company-scoped CRUD gate (source-level contract tests)."""

from __future__ import annotations

from pathlib import Path


def test_funnels_api_list_allows_tenant_catalog_without_company() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "company_id: Optional[str] = Query(None" in source
    assert "Funnel.module_key ==" in source
    assert "Funnel.company_id.isnot(None)" in source
    assert "_module_catalog_funnels" in source
    assert "if acl is not None and not acl.company_ids:" in source
    assert "Funnel.company_id.in_(list(acl.company_ids))" not in source


def test_funnels_api_create_sets_module_key_and_company() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "company_id: Optional[str] = Field(default=None" in source
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


def test_funnels_mutate_handlers_inject_userctx_not_role_string() -> None:
    """require_trust_write() returns str; ACL needs UserCtx — mixing them 500s on POST /stages."""
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "current_user: UserCtx = Depends(require_trust_write())" not in source
    assert "current_user: UserCtx = Depends(require_trust_admin())" not in source
    assert "current_user: UserCtx = Depends(get_current_user)" in source
    assert "_role: str = Depends(require_trust_write())" in source
    assert "_role: str = Depends(require_trust_admin())" in source


def test_funnels_stage_write_accepts_explicit_pe_mapping() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "pe_maps_to_code" in source
    assert "_apply_explicit_pe_mapping" in source
