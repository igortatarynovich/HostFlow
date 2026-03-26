from backend.app.constants.spa_paths import SETTINGS_BILLING
from backend.app.modules.companies.crud import OperatingCompanyLimitReached
from backend.app.modules.companies.service import _map_value_error


def test_operating_company_limit_error_maps_to_structured_402() -> None:
    exc = OperatingCompanyLimitReached(included_limit=1, extra_slots=2, effective_limit=3, used=3)
    mapped = _map_value_error(exc)
    assert mapped.status_code == 402
    assert isinstance(mapped.detail, dict)
    assert mapped.detail.get("code") == "OPERATING-COMPANY-LIMIT"
    assert mapped.detail.get("billing_path") == SETTINGS_BILLING
    assert mapped.detail.get("recommended_extra_slots") == 1
    slots = mapped.detail.get("slots") or {}
    assert slots.get("included_limit") == 1
    assert slots.get("extra_slots") == 2
    assert slots.get("effective_limit") == 3
    assert slots.get("used") == 3
    assert slots.get("available") == 0


def test_operating_company_limit_error_recommends_multiple_slots_when_gap_is_bigger() -> None:
    exc = OperatingCompanyLimitReached(included_limit=1, extra_slots=0, effective_limit=1, used=4)
    mapped = _map_value_error(exc)
    assert mapped.status_code == 402
    assert isinstance(mapped.detail, dict)
    assert mapped.detail.get("recommended_extra_slots") == 4
