from __future__ import annotations

from backend.app.entity_profile.constants import (
    WAREHOUSE_HIRING_PRESENTATION_CODE,
    WAREHOUSE_HIRING_PROFILE_CODE,
)
from backend.app.entity_profile.manifests.service_sales import service_sales_module_entity_profiles
from backend.app.entity_profile.manifests.service_sales_warehouse_hiring import (
    LABELS_PL,
    REQUIRED_CODES,
    service_sales_warehouse_hiring_profile,
)
from backend.app.entity_profile.presentation_rules import validate_presentation_rules_for_subset
from backend.app.field_registry.manifests.service_sales import service_sales_module_manifest
from backend.app.field_registry.manifests.service_sales_warehouse_hiring import (
    WAREHOUSE_HIRING_FIELD_ROWS,
    service_sales_warehouse_hiring_fields,
)


def test_warehouse_hiring_fields_are_registered_on_sales_module() -> None:
    codes = {row["qualified_code"] for row in service_sales_module_manifest()["canonical_fields"]}
    hiring = {row["qualified_code"] for row in service_sales_warehouse_hiring_fields()}
    assert hiring.issubset(codes)
    assert f"{WAREHOUSE_HIRING_PROFILE_CODE}.worker_roles" in hiring
    assert f"{WAREHOUSE_HIRING_PROFILE_CODE}.contact_company_name" in hiring


def test_warehouse_hiring_profile_is_sales_inquiry_not_candidate() -> None:
    profile = service_sales_warehouse_hiring_profile()
    assert profile["profile_code"] == WAREHOUSE_HIRING_PROFILE_CODE
    assert profile["entity_type"] == "lead"
    assert profile["module_owner"] == "service_sales"
    codes = {row["qualified_code"] for row in profile["fields"]}
    assert not any(code.startswith("recruitment.candidate.") for code in codes)
    required = {
        row["qualified_code"].rsplit(".", 1)[-1]
        for row in profile["fields"]
        if row["intake_level"] == "required"
    }
    assert required == REQUIRED_CODES


def test_warehouse_hiring_presentation_covers_every_field_and_rules() -> None:
    profile = service_sales_warehouse_hiring_profile()
    presentation = profile["intake_presentations"][0]
    assert presentation["presentation_code"] == WAREHOUSE_HIRING_PRESENTATION_CODE
    subset = presentation["field_subset"]
    assert len(subset) == len(WAREHOUSE_HIRING_FIELD_ROWS)
    field_codes = {code for code, _ftype, _name, _section in WAREHOUSE_HIRING_FIELD_ROWS}
    assert set(LABELS_PL) == field_codes
    validate_presentation_rules_for_subset(presentation["presentation_overrides"], subset)
    other_rule = presentation["presentation_overrides"][f"{WAREHOUSE_HIRING_PROFILE_CODE}.worker_roles_other"]
    assert other_rule["presentation_rules"]["show_if"]["value"] == "other"
    languages = presentation["presentation_overrides"][f"{WAREHOUSE_HIRING_PROFILE_CODE}.languages"]
    assert languages["presentation_rules"]["show_if"]["operator"] == "in"
    assert languages["presentation_rules"]["show_if"]["value"] == ["yes", "preferred"]


def test_sales_module_exposes_warehouse_hiring_beside_drivers() -> None:
    codes = [row["profile_code"] for row in service_sales_module_entity_profiles()]
    assert "service_sales.targeted_advertising" in codes
    assert "service_sales.driver_hiring" in codes
    assert WAREHOUSE_HIRING_PROFILE_CODE in codes
