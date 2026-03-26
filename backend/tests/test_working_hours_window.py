"""working_hours_v1 evaluation for lead distribution."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.services.working_hours_presets import preset_to_working_hours_v1
from backend.app.services.working_hours_window import is_within_working_hours, schedule_applies


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
