"""
Map onboarding `working_hours_preset` strings to User.extra.working_hours_v1 schedules.

Preset ids are stable API/frontend contract (see `OnboardingCompanyPage`); unknown ids are ignored.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User

from .working_hours_window import schedule_applies

TZ_WARSAW = "Europe/Warsaw"


def _mf_windows(from_h: str, to_h: str) -> list[dict[str, Any]]:
    return [{"weekday": i, "enabled": i < 5, "windows": [{"from": from_h, "to": to_h}] if i < 5 else []} for i in range(7)]


def _all_days(from_h: str, to_h: str) -> list[dict[str, Any]]:
    return [{"weekday": i, "enabled": True, "windows": [{"from": from_h, "to": to_h}]} for i in range(7)]


_PRESET_SCHEDULES: dict[str, dict[str, Any]] = {
    # Default office (PL-centric tz; user can change in My availability)
    "weekdays_9_17": {"tz": TZ_WARSAW, "days": _mf_windows("09:00", "17:00")},
    "weekdays_8_16": {"tz": TZ_WARSAW, "days": _mf_windows("08:00", "16:00")},
    "weekdays_10_18": {"tz": TZ_WARSAW, "days": _mf_windows("10:00", "18:00")},
    "weekdays_8_18": {"tz": TZ_WARSAW, "days": _mf_windows("08:00", "18:00")},
    "shift_mornings": {"tz": TZ_WARSAW, "days": _mf_windows("06:00", "14:00")},
    "shift_afternoons": {"tz": TZ_WARSAW, "days": _mf_windows("14:00", "22:00")},
    "seven_day_9_17": {"tz": TZ_WARSAW, "days": _all_days("09:00", "17:00")},
    # Always inside window → criterion "working_hours" never filters them out by calendar
    "always_available": {"tz": None, "days": _all_days("00:00", "23:59")},
}


def preset_to_working_hours_v1(preset_id: str) -> dict[str, Any] | None:
    key = str(preset_id or "").strip().lower().replace("-", "_")
    if not key:
        return None
    row = _PRESET_SCHEDULES.get(key)
    if row is None:
        return None
    return {"tz": row["tz"], "days": [dict(d) for d in row["days"]]}


async def apply_working_hours_preset_to_user_if_empty(
    db: AsyncSession,
    *,
    user_id: str,
    preset: str | None,
) -> None:
    """If user has no working_hours_v1 windows yet, seed from preset (onboarding)."""
    uid = str(user_id or "").strip()
    if not uid:
        return
    sched = preset_to_working_hours_v1(str(preset or "").strip())
    if sched is None:
        return
    row = await db.execute(select(User).where(User.id == uid).limit(1))
    user = row.scalar_one_or_none()
    if user is None:
        return
    extra = dict(user.extra or {}) if isinstance(user.extra, dict) else {}
    if schedule_applies(extra):
        return
    extra["working_hours_v1"] = sched
    user.extra = extra
    db.add(user)
    await db.flush()
