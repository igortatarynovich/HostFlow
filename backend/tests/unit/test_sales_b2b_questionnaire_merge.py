from __future__ import annotations

from types import SimpleNamespace

from backend.app.entity_profile.public_intake_presentation_bridge import apply_presentation_values_to_state
from backend.app.intake_platform.form_definition import resolve_create_form_languages
from backend.app.modules.leads.lead_questionnaire_invite import merge_presentation_into_sales_summary


def test_resolve_create_form_languages_custom_single() -> None:
    default, supported = resolve_create_form_languages(default_language="ru", supported_languages=["ru"])
    assert default == "ru"
    assert supported == ["ru"]


def test_resolve_create_form_languages_preset_default() -> None:
    default, supported = resolve_create_form_languages(
        default_language="en",
        supported_languages=["pl", "en", "ru"],
    )
    assert default == "en"
    assert supported == ["pl", "en", "ru"]


def test_bridge_copies_driver_hiring_contacts() -> None:
    state: dict = {}
    apply_presentation_values_to_state(
        state,
        {
            "service_sales.driver_hiring.contact_company_name": "Trans Polska",
            "service_sales.driver_hiring.contact_full_name": "Anna Nowak",
            "service_sales.driver_hiring.contact_email": "anna@example.com",
            "service_sales.driver_hiring.contact_phone": "+48123456789",
        },
    )
    assert state["client_company"]["name"] == "Trans Polska"
    assert state["personal"]["full_name"] == "Anna Nowak"
    assert state["contacts"]["email"] == "anna@example.com"
    assert state["contacts"]["phone"] == "+48123456789"


def test_merge_keeps_platform_widget_and_rules() -> None:
    from backend.app.entity_profile.presentation_write import merge_client_fields_with_platform_preset

    merged = merge_client_fields_with_platform_preset(
        [
            {
                "qualified_code": "service_sales.driver_hiring.driver_categories",
                "intake_level": "required",
                "sort_order": 10,
            }
        ],
        [
            {
                "qualified_code": "service_sales.driver_hiring.driver_categories",
                "widget_hint": "multi_select",
                "presentation_rules": {
                    "show_if": {
                        "source_field": "service_sales.driver_hiring.drivers_needed",
                        "operator": "truthy",
                    }
                },
            }
        ],
    )
    assert merged[0]["widget_hint"] == "multi_select"
    assert merged[0]["presentation_rules"]["show_if"]["source_field"].endswith("drivers_needed")


def test_public_form_profile_code_fits_column() -> None:
    from backend.app.services.intake_form_write_service import _public_form_profile_code

    long_slug = "x" * 64
    code = _public_form_profile_code(long_slug)
    assert len(code) <= 64
    assert code.startswith("public-form-")


def test_create_in_coerces_underscore_slug_and_bad_rule_operator() -> None:
    from backend.app.api.v1.settings.intake_forms import IntakeFormCreateIn

    payload = IntakeFormCreateIn.model_validate(
        {
            "title": "Drivers",
            "public_slug": "company_needs_drivers",
            "entity_profile_code": "service_sales.driver_hiring",
            "fields": [
                {
                    "qualified_code": "service_sales.driver_hiring.contact_email",
                    "intake_level": "required",
                    "presentation_rules": {
                        "show_if": {
                            "source_field": "service_sales.driver_hiring.contact_phone",
                            "operator": "contains",
                            "value": "x",
                        }
                    },
                }
            ],
        }
    )
    assert payload.public_slug == "company-needs-drivers"
    assert payload.fields[0].presentation_rules is not None
    assert payload.fields[0].presentation_rules.show_if is not None
    assert payload.fields[0].presentation_rules.show_if.operator == "eq"


def test_merge_driver_hiring_answers_keeps_profile_and_contacts() -> None:
    lead = SimpleNamespace(normalized={}, payload={}, stage="new")
    state = {
        "entity_profile_code": "service_sales.driver_hiring",
        "presentation_values_v1": {
            "service_sales.driver_hiring.contact_company_name": "Trans Polska",
            "service_sales.driver_hiring.contact_email": "anna@example.com",
            "service_sales.driver_hiring.contact_phone": "+48123456789",
            "service_sales.driver_hiring.drivers_needed": 4,
        },
        "contacts": {},
        "client_company": {},
        "personal": {},
    }
    apply_presentation_values_to_state(state, dict(state["presentation_values_v1"]))
    out = merge_presentation_into_sales_summary(lead, state, submitted=True)
    assert out["entity_profile_code"] == "service_sales.driver_hiring"
    assert out["company_name"] == "Trans Polska"
    assert out["email"] == "anna@example.com"
    assert out["phone"] == "+48123456789"
    assert out["sales_questionnaire"]["drivers_needed"] == 4
