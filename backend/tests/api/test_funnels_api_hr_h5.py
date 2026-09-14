"""H5 — HR employee funnel API + CMS contracts."""

from __future__ import annotations

from backend.tests.test_support.repo_paths import read_repo_text


def test_funnels_api_imports_hr_module_key() -> None:
    import backend.app.api.v1.funnels as funnels
    from backend.app.constants.funnel_types import HR_MODULE_KEY

    assert getattr(funnels, "HR_MODULE_KEY", None) is HR_MODULE_KEY


def test_funnels_api_list_supports_hr_module_key() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "HR_MODULE_KEY" in source
    assert "_enforce_company_module_scope" in source
    assert "module_key=HR_MODULE_KEY" in source


def test_funnels_api_create_hr_employee_branch() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "is_hr_employee_funnel_type(payload.type)" in source
    assert "module_key=HR_MODULE_KEY" in source
    assert "type=HR_EMPLOYEE_FUNNEL_TYPE" in source


def test_funnels_api_recruitment_create_does_not_use_employee_type() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "Recruitment funnels cannot use type=employee" in source


def test_company_module_settings_validates_hr_pipeline_funnel() -> None:
    source = read_repo_text("backend/app/api/v1/company_module_settings.py")
    assert "validate_hr_module_settings_for_company" in source
    assert 'if mk == "hr"' in source


def test_hr_cms_validation_rejects_recruitment_module() -> None:
    source = read_repo_text("backend/app/services/hr_employee_funnel_resolver.py")
    assert "validate_hr_module_settings_for_company" in source
    assert "employee_pipeline_funnel_id must use module_key=hr" in source
