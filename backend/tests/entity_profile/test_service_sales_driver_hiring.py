from __future__ import annotations

from backend.app.entity_profile.constants import (
    DRIVER_HIRING_PRESENTATION_CODE,
    DRIVER_HIRING_PROFILE_CODE,
)
from backend.app.entity_profile.manifests.service_sales import service_sales_module_entity_profiles
from backend.app.entity_profile.manifests.service_sales_driver_hiring import (
    REQUIRED_CODES,
    service_sales_driver_hiring_profile,
)
from backend.app.entity_profile.presentation_rules import validate_presentation_rules_for_subset
from backend.app.field_registry.manifests.service_sales import service_sales_module_manifest
from backend.app.field_registry.manifests.service_sales_driver_hiring import (
    DRIVER_HIRING_FIELD_ROWS,
    service_sales_driver_hiring_fields,
)


def test_driver_hiring_fields_are_registered_on_sales_module() -> None:
    codes = {row["qualified_code"] for row in service_sales_module_manifest()["canonical_fields"]}
    hiring = {row["qualified_code"] for row in service_sales_driver_hiring_fields()}
    assert hiring.issubset(codes)
    assert f"{DRIVER_HIRING_PROFILE_CODE}.driver_categories" in hiring
    assert f"{DRIVER_HIRING_PROFILE_CODE}.contact_company_name" in hiring


def test_driver_hiring_profile_is_sales_inquiry_not_candidate() -> None:
    profile = service_sales_driver_hiring_profile()
    assert profile["profile_code"] == DRIVER_HIRING_PROFILE_CODE
    assert profile["entity_type"] == "lead"
    assert profile["module_owner"] == "service_sales"
    codes = {row["qualified_code"] for row in profile["fields"]}
    assert not any(code.startswith("recruitment.candidate.") for code in codes)
    required = {row["qualified_code"].rsplit(".", 1)[-1] for row in profile["fields"] if row["intake_level"] == "required"}
    assert required == REQUIRED_CODES


def test_driver_hiring_presentation_covers_every_field_and_rules() -> None:
    profile = service_sales_driver_hiring_profile()
    presentation = profile["intake_presentations"][0]
    assert presentation["presentation_code"] == DRIVER_HIRING_PRESENTATION_CODE
    subset = presentation["field_subset"]
    assert len(subset) == len(DRIVER_HIRING_FIELD_ROWS)
    validate_presentation_rules_for_subset(presentation["presentation_overrides"], subset)
    other_rule = presentation["presentation_overrides"][f"{DRIVER_HIRING_PROFILE_CODE}.driver_categories_other"]
    assert other_rule["presentation_rules"]["show_if"]["value"] == "other"


def test_sales_module_exposes_driver_hiring_beside_ads() -> None:
    codes = [row["profile_code"] for row in service_sales_module_entity_profiles()]
    assert "service_sales.targeted_advertising" in codes
    assert DRIVER_HIRING_PROFILE_CODE in codes
