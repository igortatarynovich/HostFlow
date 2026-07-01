from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.services.notification_settings_v1 import (
    is_within_quiet_hours_v1,
    normalize_notification_settings_v1,
    should_skip_in_app_notification_v1,
)


def test_normalize_defaults() -> None:
    s = normalize_notification_settings_v1({})
    assert s["channels"]["in_app"] is True
    assert s["quiet_hours_enabled"] is False


@pytest.mark.parametrize(
    ("now_iso", "expected"),
    [
        ("2026-04-22T23:30:00+00:00", True),
        ("2026-04-22T10:00:00+00:00", False),
        ("2026-04-22T07:30:00+00:00", True),
    ],
)
def test_quiet_hours_overnight_utc(now_iso: str, expected: bool) -> None:
    s = normalize_notification_settings_v1(
        {
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "timezone": "UTC",
        }
    )
    now = datetime.fromisoformat(now_iso)
    assert is_within_quiet_hours_v1(s, now_utc=now) is expected


def test_skip_in_app_respects_channel_toggle() -> None:
    s = normalize_notification_settings_v1({"channels": {"in_app": False}})
    assert should_skip_in_app_notification_v1(s, now_utc=datetime.now(timezone.utc), resolved_priority="critical", channel="in_app") is True


def test_critical_bypasses_quiet_hours() -> None:
    s = normalize_notification_settings_v1(
        {
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "timezone": "UTC",
        }
    )
    now = datetime.fromisoformat("2026-04-22T23:30:00+00:00")
    assert should_skip_in_app_notification_v1(s, now_utc=now, resolved_priority="critical", channel="in_app") is False


def test_high_suppressed_during_quiet() -> None:
    s = normalize_notification_settings_v1(
        {
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "timezone": "UTC",
        }
    )
    now = datetime.fromisoformat("2026-04-22T23:30:00+00:00")
    assert should_skip_in_app_notification_v1(s, now_utc=now, resolved_priority="high", channel="in_app") is True
