from backend.app.services.operating_company_slots import (
    extract_extra_operating_company_slots,
    extract_extra_operating_company_slots_from_tenant_settings,
    resolve_effective_company_limit,
)


def test_extract_extra_operating_company_slots_from_subscription_payload() -> None:
    assert extract_extra_operating_company_slots({"extra_operating_company_slots": 2}) == 2
    assert extract_extra_operating_company_slots({"additional_operating_company_slots": "3"}) == 3
    assert extract_extra_operating_company_slots({"operating_company_addon_slots": 1}) == 1
    assert extract_extra_operating_company_slots({"extra_operating_company_slots": -5}) == 0
    assert extract_extra_operating_company_slots({}) == 0


def test_extract_extra_operating_company_slots_from_tenant_settings() -> None:
    settings = {
        "billing": {
            "subscription": {
                "extra_operating_company_slots": 4,
            }
        }
    }
    assert extract_extra_operating_company_slots_from_tenant_settings(settings) == 4
    assert extract_extra_operating_company_slots_from_tenant_settings({}) == 0


def test_resolve_effective_company_limit() -> None:
    assert resolve_effective_company_limit(1, 0) == 1
    assert resolve_effective_company_limit(1, 2) == 3
    # 0 remains unlimited and should not be converted to finite limit.
    assert resolve_effective_company_limit(0, 5) == 0
