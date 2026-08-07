"""H5 — HR employee funnel API + CMS contracts."""

from __future__ import annotations

from pathlib import Path


def test_funnels_api_list_supports_hr_module_key() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "HR_MODULE_KEY" in source
    assert "HR_MODULE_KEY," in source or "HR_MODULE_KEY\n" in source
    assert "_enforce_company_module_scope" in source
    assert "module_key=HR_MODULE_KEY" in source
    # Runtime guard: NameError here is exactly the production /funnels 500.
    from backend.app.api.v1 import funnels as funnels_api

    assert funnels_api.HR_MODULE_KEY == "hr"
    assert "recruitment" in {
        funnels_api.RECRUITMENT_MODULE_KEY,
        funnels_api.HR_MODULE_KEY,
    }

def test_funnels_api_create_hr_employee_branch() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "is_hr_employee_funnel_type(payload.type)" in source
    assert "module_key=HR_MODULE_KEY" in source
    assert "type=HR_EMPLOYEE_FUNNEL_TYPE" in source


def test_funnels_api_recruitment_create_does_not_use_employee_type() -> None:
    source = Path("backend/app/api/v1/funnels.py").read_text(encoding="utf-8")
    assert "Recruitment funnels cannot use type=employee" in source


def test_company_module_settings_validates_hr_pipeline_funnel() -> None:
    source = Path("backend/app/api/v1/company_module_settings.py").read_text(encoding="utf-8")
    assert "validate_hr_module_settings_for_company" in source
    assert 'if mk == "hr"' in source


def test_hr_cms_validation_rejects_recruitment_module() -> None:
    source = Path("backend/app/services/hr_employee_funnel_resolver.py").read_text(encoding="utf-8")
    assert "validate_hr_module_settings_for_company" in source
    assert "employee_pipeline_funnel_id must use module_key=hr" in source
