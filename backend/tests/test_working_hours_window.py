"""working_hours_v1 evaluation for lead distribution + G-4 schedule shift."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend.app.services.working_hours_presets import preset_to_working_hours_v1
from backend.app.services.working_hours_window import (
    is_within_working_hours,
    next_working_window_after,
    schedule_applies,
)


def test_schedule_applies_false_when_empty() -> None:
    assert schedule_applies({}) is False
    assert schedule_applies({"working_hours_v1": {"tz": None, "days": []}}) is False


def test_weekdays_9_17_monday_inside_warsaw() -> None:
    sched = preset_to_working_hours_v1("weekdays_9_17")
    assert sched is not None
    extra = {"working_hours_v1": sched}
    assert schedule_applies(extra) is True
    # 2025-06-02 Monday 08:00 UTC ≈ 10:00 Europe/Warsaw (CEST)
    dt = datetime(2025, 6, 2, 8, 0, tzinfo=timezone.utc)
    assert is_within_working_hours(extra, dt) is True


def test_weekdays_9_17_saturday_outside() -> None:
    sched = preset_to_working_hours_v1("weekdays_9_17")
    extra = {"working_hours_v1": sched}
    dt = datetime(2025, 6, 7, 8, 0, tzinfo=timezone.utc)
    assert is_within_working_hours(extra, dt) is False


def test_no_schedule_always_within() -> None:
    assert is_within_working_hours({}, datetime(2025, 6, 7, 0, 0, tzinfo=timezone.utc)) is True


# ---------------------------------------------------------------------------
# G-4 stage 1: next_working_window_after
#
# These tests anchor against `Europe/Warsaw` because the default presets
# use that tz (CEST in June = UTC+2, CET in January = UTC+1). Each test
# documents the local-time intent in a comment, then asserts UTC.
# ---------------------------------------------------------------------------


def _warsaw_extra() -> dict:
    sched = preset_to_working_hours_v1("weekdays_9_17")
    assert sched is not None
    return {"working_hours_v1": sched}


def test_next_window_returns_unchanged_inside_window() -> None:
    """Already inside a window — must return ref unchanged (preserves
    seconds/microseconds, no spurious rounding)."""
    extra = _warsaw_extra()
    # Monday 2025-06-02 08:00 UTC = 10:00 Warsaw — inside 09:00-17:00.
    ref = datetime(2025, 6, 2, 8, 0, 17, 123, tzinfo=timezone.utc)
    out = next_working_window_after(extra, ref)
    assert out == ref


def test_next_window_shifts_from_early_morning_to_9am_local() -> None:
    """Reminder set for 03:00 local Monday — should shift to 09:00 local
    same day (07:00 UTC during CEST)."""
    extra = _warsaw_extra()
    # Monday 2025-06-02 01:00 UTC = 03:00 Warsaw — too early.
    ref = datetime(2025, 6, 2, 1, 0, tzinfo=timezone.utc)
    out = next_working_window_after(extra, ref)
    # Expected 09:00 Warsaw = 07:00 UTC
    assert out == datetime(2025, 6, 2, 7, 0, tzinfo=timezone.utc)


def test_next_window_shifts_from_late_evening_to_next_day_9am() -> None:
    """Past 17:00 local — must skip to next day's 09:00."""
    extra = _warsaw_extra()
    # Monday 2025-06-02 19:00 UTC = 21:00 Warsaw — past 17:00.
    ref = datetime(2025, 6, 2, 19, 0, tzinfo=timezone.utc)
    out = next_working_window_after(extra, ref)
    # Tuesday 2025-06-03 09:00 Warsaw = 07:00 UTC
    assert out == datetime(2025, 6, 3, 7, 0, tzinfo=timezone.utc)


def test_next_window_skips_disabled_weekend_to_monday() -> None:
    """Saturday → Sunday → first window is Monday 09:00. Confirms the
    14-day forward walk skips disabled weekdays correctly."""
    extra = _warsaw_extra()
    # Saturday 2025-06-07 14:00 UTC = 16:00 Warsaw.
    ref = datetime(2025, 6, 7, 14, 0, tzinfo=timezone.utc)
    out = next_working_window_after(extra, ref)
    # Monday 2025-06-09 09:00 Warsaw = 07:00 UTC
    assert out == datetime(2025, 6, 9, 7, 0, tzinfo=timezone.utc)


def test_next_window_no_schedule_returns_unchanged() -> None:
    """No schedule configured — helper is a no-op (callers treat
    'no schedule' as 'anytime is fine')."""
    ref = datetime(2025, 6, 2, 1, 0, tzinfo=timezone.utc)
    assert next_working_window_after({}, ref) == ref
    # `schedule_applies` False because all-empty days
    extra = {"working_hours_v1": {"tz": "Europe/Warsaw", "days": []}}
    assert next_working_window_after(extra, ref) == ref


def test_next_window_naive_input_treated_as_utc() -> None:
    """Mirror the policy of `is_within_working_hours`: naive datetimes
    are interpreted as UTC, not local time."""
    extra = _warsaw_extra()
    # Naive 03:00 — same as 03:00 UTC = 05:00 Warsaw → still too early.
    ref_naive = datetime(2025, 6, 2, 3, 0)
    out = next_working_window_after(extra, ref_naive)
    # Should produce 09:00 Warsaw = 07:00 UTC
    assert out == datetime(2025, 6, 2, 7, 0, tzinfo=timezone.utc)
    assert out.tzinfo is not None


def test_next_window_dst_winter_warsaw_offset_changes() -> None:
    """In January Warsaw is CET (UTC+1), not CEST. Same local 09:00 →
    08:00 UTC. Regression guard: zoneinfo correctly handles DST."""
    extra = _warsaw_extra()
    # Monday 2025-01-06 06:00 UTC = 07:00 Warsaw — too early.
    ref = datetime(2025, 1, 6, 6, 0, tzinfo=timezone.utc)
    out = next_working_window_after(extra, ref)
    # 09:00 Warsaw (CET) = 08:00 UTC
    assert out == datetime(2025, 1, 6, 8, 0, tzinfo=timezone.utc)


def test_next_window_multiple_windows_picks_later_same_day() -> None:
    """If the day has split windows (e.g. 09-12, 14-17) and ref is at
    13:00, must shift to 14:00 not skip to next day."""
    extra = {
        "working_hours_v1": {
            "tz": "Europe/Warsaw",
            "days": [
                {
                    "weekday": 0,  # Monday
                    "enabled": True,
                    "windows": [
                        {"from": "09:00", "to": "12:00"},
                        {"from": "14:00", "to": "17:00"},
                    ],
                }
            ],
        }
    }
    # Monday 2025-06-02 11:00 UTC = 13:00 Warsaw — between windows.
    ref = datetime(2025, 6, 2, 11, 0, tzinfo=timezone.utc)
    out = next_working_window_after(extra, ref)
    # 14:00 Warsaw = 12:00 UTC
    assert out == datetime(2025, 6, 2, 12, 0, tzinfo=timezone.utc)


def test_next_window_returns_utc_aware_when_local_tz_used() -> None:
    """Even when we walk in local tz internally, the return must be UTC
    aware (callers persist UTC-aware datetimes)."""
    extra = _warsaw_extra()
    ref = datetime(2025, 6, 2, 1, 0, tzinfo=timezone.utc)
    out = next_working_window_after(extra, ref)
    assert out.tzinfo is not None
    # Confirm it actually represents the right UTC instant by re-converting
    local = out.astimezone(ZoneInfo("Europe/Warsaw"))
    assert local.hour == 9 and local.minute == 0
