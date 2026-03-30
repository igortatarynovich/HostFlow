"""Unit tests for automation rule condition matching (§2.10 / reminders)."""

from __future__ import annotations

import pytest

from backend.app.services.automation_rules import _matches_conditions


@pytest.mark.parametrize(
    "conditions,ctx,expected",
    [
        ({}, {"a": 1}, True),
        ({"stage": "contacted"}, {"stage": "contacted"}, True),
        ({"stage": "contacted"}, {"stage": "other"}, False),
        ({"nested.x": "1"}, {"nested": {"x": "1"}}, True),
        ({"nested.x": "1"}, {"nested": {}}, False),
        ({"missing": None}, {"missing": None}, True),
        ({"missing": None}, {"missing": "x"}, False),
        ({"source": "META"}, {"source": "meta"}, True),
        ({"source": "meta"}, {"source": "META"}, True),
        (
            {"normalized.country": {"op": "in", "value": ["PL", "DE"]}},
            {"normalized": {"country": "DE"}},
            True,
        ),
        (
            {"normalized.country": {"op": "in", "value": ["PL", "DE"]}},
            {"normalized": {"country": "FR"}},
            False,
        ),
        (
            {"normalized.country": {"op": "neq", "value": "PL"}},
            {"normalized": {"country": "DE"}},
            True,
        ),
        (
            {"normalized.country": {"op": "neq", "value": "PL"}},
            {"normalized": {"country": "PL"}},
            False,
        ),
        (
            {"normalized.country": {"op": "neq", "value": "PL"}},
            {"normalized": {}},
            True,
        ),
        (
            {"normalized.country": {"op": "exists"}},
            {"normalized": {"country": "PL"}},
            True,
        ),
        (
            {"normalized.country": {"op": "exists"}},
            {"normalized": {"country": ""}},
            False,
        ),
        (
            {"normalized.country": {"op": "exists"}},
            {"normalized": {}},
            False,
        ),
        (
            {"normalized.country": {"op": "not_exists"}},
            {"normalized": {}},
            True,
        ),
        (
            {"normalized.country": {"op": "not_exists"}},
            {"normalized": {"country": "PL"}},
            False,
        ),
        (
            {
                "$and": [
                    {"source": "meta"},
                    {"normalized.country": {"op": "eq", "value": "PL"}},
                ]
            },
            {"source": "meta", "normalized": {"country": "PL"}},
            True,
        ),
        (
            {
                "$and": [
                    {"source": "meta"},
                    {"normalized.country": {"op": "eq", "value": "PL"}},
                ]
            },
            {"source": "meta", "normalized": {"country": "DE"}},
            False,
        ),
    ],
)
def test_matches_conditions(conditions, ctx, expected):
    assert _matches_conditions(conditions, ctx) is expected


def test_implicit_and_multiple_keys():
    ctx = {"source": "meta", "normalized": {"country": "PL", "city": "WAW"}}
    assert (
        _matches_conditions(
            {
                "source": "meta",
                "normalized.country": "PL",
                "normalized.city": "WAW",
            },
            ctx,
        )
        is True
    )
    assert (
        _matches_conditions(
            {
                "source": "meta",
                "normalized.country": "PL",
                "normalized.city": "KRK",
            },
            ctx,
        )
        is False
    )
