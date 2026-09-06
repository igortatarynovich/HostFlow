"""H1: funnel type schema contracts (employee + recruitment types)."""

from __future__ import annotations
import pytest

from backend.app.constants.funnel_types import (
    ALL_OPERATIONAL_FUNNEL_TYPES,
    FUNNEL_TYPE_PATTERN,
    HR_EMPLOYEE_FUNNEL_TYPE,
    RECRUITMENT_FUNNEL_TYPES,
    module_key_for_funnel_type,
    validate_funnel_type,
)
from backend.tests.test_support.repo_paths import read_repo_text


def test_funnel_types_include_employee_without_changing_recruitment_set() -> None:
    assert RECRUITMENT_FUNNEL_TYPES == frozenset({"candidate", "lead", "deal"})
    assert HR_EMPLOYEE_FUNNEL_TYPE == "employee"
    assert HR_EMPLOYEE_FUNNEL_TYPE in ALL_OPERATIONAL_FUNNEL_TYPES
    assert HR_EMPLOYEE_FUNNEL_TYPE not in RECRUITMENT_FUNNEL_TYPES


def test_module_key_for_funnel_type_maps_hr_employee() -> None:
    assert module_key_for_funnel_type("candidate") == "recruitment"
    assert module_key_for_funnel_type("employee") == "hr"
    assert module_key_for_funnel_type("unknown") is None


def test_validate_funnel_type_accepts_employee() -> None:
    assert validate_funnel_type("employee") == "employee"
    assert validate_funnel_type("candidate") == "candidate"


def test_validate_funnel_type_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        validate_funnel_type("hr_case")


def test_funnels_api_pydantic_allows_employee_type_in_schema() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "FUNNEL_TYPE_PATTERN" in source
    assert "pattern=FUNNEL_TYPE_PATTERN" in source
    assert "is_hr_employee_funnel_type" in source


def test_funnels_api_recruitment_create_routes_employee_to_hr_module() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "is_hr_employee_funnel_type(payload.type)" in source
    assert "module_key=HR_MODULE_KEY" in source
    assert "Recruitment funnels cannot use type=employee" in source


def test_hr_employee_funnel_resolver_module_is_hr() -> None:
    source = read_repo_text("backend/app/services/hr_employee_funnel_resolver.py")
    assert "async def resolve_hr_employee_funnel" in source
    assert "HR_MODULE_KEY" in source
    assert "HR_EMPLOYEE_FUNNEL_TYPE" in source
    assert "employee_pipeline_funnel_id" in source
    assert "resolve_recruitment_funnel" not in source
