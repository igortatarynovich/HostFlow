from backend.app.api.v1.settings import billing


def test_extract_operating_slot_addon_quantity_returns_none_without_price_config() -> None:
    previous = billing.settings.stripe_price_operating_company_slot
    billing.settings.stripe_price_operating_company_slot = None
    try:
        assert billing._extract_operating_slot_addon_quantity({}) is None
    finally:
        billing.settings.stripe_price_operating_company_slot = previous


def test_extract_operating_slot_addon_quantity_reads_subscription_item_quantity() -> None:
    previous = billing.settings.stripe_price_operating_company_slot
    billing.settings.stripe_price_operating_company_slot = "price_slot_addon"
    try:
        sub_obj = {
            "items": {
                "data": [
                    {"id": "si_base", "price": {"id": "price_base"}, "quantity": 1},
                    {"id": "si_addon", "price": {"id": "price_slot_addon"}, "quantity": 3},
                ]
            }
        }
        assert billing._extract_operating_slot_addon_quantity(sub_obj) == 3
    finally:
        billing.settings.stripe_price_operating_company_slot = previous


def test_extract_operating_slot_addon_quantity_returns_zero_when_addon_absent() -> None:
    previous = billing.settings.stripe_price_operating_company_slot
    billing.settings.stripe_price_operating_company_slot = "price_slot_addon"
    try:
        sub_obj = {"items": {"data": [{"id": "si_base", "price": {"id": "price_base"}, "quantity": 1}]}}
        assert billing._extract_operating_slot_addon_quantity(sub_obj) == 0
    finally:
        billing.settings.stripe_price_operating_company_slot = previous


def test_extract_operating_slot_addon_quantity_defaults_to_one_when_quantity_missing() -> None:
    previous = billing.settings.stripe_price_operating_company_slot
    billing.settings.stripe_price_operating_company_slot = "price_slot_addon"
    try:
        sub_obj = {"items": {"data": [{"id": "si_addon", "price": {"id": "price_slot_addon"}}]}}
        assert billing._extract_operating_slot_addon_quantity(sub_obj) == 1
    finally:
        billing.settings.stripe_price_operating_company_slot = previous


def test_operating_slot_addon_price_id_for_plan_prefers_team_business_specific() -> None:
    prev_t = billing.settings.stripe_price_operating_company_slot_team
    prev_b = billing.settings.stripe_price_operating_company_slot_business
    prev_l = billing.settings.stripe_price_operating_company_slot
    try:
        billing.settings.stripe_price_operating_company_slot_team = "price_team_ws"
        billing.settings.stripe_price_operating_company_slot_business = "price_bus_ws"
        billing.settings.stripe_price_operating_company_slot = "price_legacy_ws"
        assert billing._operating_slot_addon_price_id_for_plan("team") == "price_team_ws"
        assert billing._operating_slot_addon_price_id_for_plan("pro") == "price_bus_ws"
        assert billing._operating_slot_addon_price_id_for_plan("starter") == "price_legacy_ws"
    finally:
        billing.settings.stripe_price_operating_company_slot_team = prev_t
        billing.settings.stripe_price_operating_company_slot_business = prev_b
        billing.settings.stripe_price_operating_company_slot = prev_l


def test_extract_operating_slot_matches_any_configured_workspace_slot_price() -> None:
    prev_t = billing.settings.stripe_price_operating_company_slot_team
    prev_b = billing.settings.stripe_price_operating_company_slot_business
    prev_l = billing.settings.stripe_price_operating_company_slot
    try:
        billing.settings.stripe_price_operating_company_slot_team = "price_team_ws"
        billing.settings.stripe_price_operating_company_slot_business = "price_bus_ws"
        billing.settings.stripe_price_operating_company_slot = None
        sub_obj = {
            "items": {
                "data": [
                    {"id": "si_base", "price": {"id": "price_base"}, "quantity": 1},
                    {"id": "si_ws", "price": {"id": "price_bus_ws"}, "quantity": 4},
                ]
            }
        }
        assert billing._extract_operating_slot_addon_quantity(sub_obj) == 4
    finally:
        billing.settings.stripe_price_operating_company_slot_team = prev_t
        billing.settings.stripe_price_operating_company_slot_business = prev_b
        billing.settings.stripe_price_operating_company_slot = prev_l
