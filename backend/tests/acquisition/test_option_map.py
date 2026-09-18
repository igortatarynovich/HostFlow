"""Option-map key matching for Graph snake_case vs operator labels."""

from backend.app.field_registry.option_map import (
    OPTION_IGNORE_VALUE,
    lookup_option_map,
    option_map_covers,
)


def test_lookup_matches_underscore_and_case() -> None:
    option_map = {"Виза": "Wiza", "Более 2 лет": "2+"}
    assert lookup_option_map(option_map, "виза") == "Wiza"
    assert lookup_option_map(option_map, "более_2_лет") == "2+"
    assert lookup_option_map(option_map, "unknown") is None


def test_lookup_ignore_sentinel() -> None:
    assert lookup_option_map({"Нет": OPTION_IGNORE_VALUE}, "нет") == OPTION_IGNORE_VALUE


def test_covers_snake_case_schema_options() -> None:
    option_map = {"Более 2 лет": "2+", "До 6 месяцев": "0.5"}
    assert option_map_covers(option_map, ["более_2_лет", "до_6_месяцев"]) is True
    assert option_map_covers(option_map, ["более_2_лет", "нет"]) is False
