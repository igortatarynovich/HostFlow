"""§2.16 enforcement slice: automation rule caps, file size aggregation (unit-level)."""

from __future__ import annotations

import pytest

from backend.app.services.plan_feature_gates import (
    automation_rules_enabled_cap,
    communication_channel_accounts_cap_for_bucket,
    custom_funnel_definitions_cap_for_bucket,
    plan_bucket_for_limits,
)
from backend.app.services.tenant_quota import sum_file_entries_bytes


@pytest.mark.parametrize(
    "plan,expected",
    [
        ("starter", None),
        ("trial", None),
        ("free", None),
        ("solo", None),
        ("team", 10),
        ("pro", 50),
        ("custom", 50),
    ],
)
def test_automation_rules_enabled_cap(plan: str, expected: int | None) -> None:
    assert automation_rules_enabled_cap(plan) == expected


@pytest.mark.parametrize(
    ("plan", "bucket"),
    [
        ("starter", "starter"),
        ("trial", "starter"),
        ("agency_basic", "team"),
        ("team", "team"),
        ("business", "pro"),
        ("pro", "pro"),
    ],
)
def test_plan_bucket_for_limits(plan: str, bucket: str) -> None:
    assert plan_bucket_for_limits(plan) == bucket


@pytest.mark.parametrize(
    ("bucket", "expected"),
    [("starter", 1), ("team", 3), ("pro", 10)],
)
def test_communication_channel_cap(bucket: str, expected: int) -> None:
    assert communication_channel_accounts_cap_for_bucket(bucket) == expected


@pytest.mark.parametrize(
    ("bucket", "expected"),
    [("starter", 1), ("team", 3), ("pro", 20)],
)
def test_custom_funnel_cap(bucket: str, expected: int) -> None:
    assert custom_funnel_definitions_cap_for_bucket(bucket) == expected


def test_sum_file_entries_bytes_handles_mixed() -> None:
    assert sum_file_entries_bytes(None) == 0
    assert sum_file_entries_bytes([]) == 0
    assert sum_file_entries_bytes([{"size": 100}, {"size": "50"}]) == 150
    assert sum_file_entries_bytes([{"n": 1}, {"size": "x"}]) == 0
