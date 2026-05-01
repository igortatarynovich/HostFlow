"""Shared normalization + quiet-hours helpers for ``User.extra['notification_settings_v1']``."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

_CLOCK_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")


def normalize_notification_settings_v1(raw: Any) -> dict[str, Any]:
    """Same shape as API ``NotificationSettingsOut`` / planner persistence."""
    src = dict(raw or {}) if isinstance(raw, dict) else {}
    try:
        default_reminder_minutes = int(src.get("default_reminder_minutes", 30))
    except Exception:
        default_reminder_minutes = 30
    if default_reminder_minutes < 0:
        default_reminder_minutes = 0
    if default_reminder_minutes > 1440:
        default_reminder_minutes = 1440
    channels_raw = src.get("channels")
    channels = {
        "in_app": True,
        "push": True,
        "email": False,
    }
    if isinstance(channels_raw, dict):
        channels["in_app"] = bool(channels_raw.get("in_app", channels["in_app"]))
        channels["push"] = bool(channels_raw.get("push", channels["push"]))
        channels["email"] = bool(channels_raw.get("email", channels["email"]))
    quiet_hours_enabled = bool(src.get("quiet_hours_enabled", False))
    quiet_hours_start = str(src.get("quiet_hours_start") or "").strip() or None
    quiet_hours_end = str(src.get("quiet_hours_end") or "").strip() or None
    if quiet_hours_start and not _CLOCK_HHMM_RE.match(quiet_hours_start):
        quiet_hours_start = None
    if quiet_hours_end and not _CLOCK_HHMM_RE.match(quiet_hours_end):
        quiet_hours_end = None
    timezone_val = str(src.get("timezone") or "").strip() or None
    return {
        "default_reminder_minutes": default_reminder_minutes,
        "channels": channels,
        "quiet_hours_enabled": quiet_hours_enabled,
        "quiet_hours_start": quiet_hours_start,
        "quiet_hours_end": quiet_hours_end,
        "timezone": timezone_val,
    }


def _parse_hhmm_to_minutes(clock: str) -> int | None:
    if not clock or not _CLOCK_HHMM_RE.match(clock):
        return None
    h, m = clock.split(":", 1)
    try:
        hi = int(h)
        mi = int(m)
    except Exception:
        return None
    if hi < 0 or hi > 23 or mi < 0 or mi > 59:
        return None
    return hi * 60 + mi


def _local_minutes_from_utc(now_utc: datetime, tz_name: str | None) -> int:
    name = (tz_name or "").strip() or "UTC"
    try:
        tz = ZoneInfo(name)
    except Exception:
        tz = ZoneInfo("UTC")
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    local = now_utc.astimezone(tz)
    return local.hour * 60 + local.minute


def is_within_quiet_hours_v1(settings: dict[str, Any], *, now_utc: datetime) -> bool:
    if not bool(settings.get("quiet_hours_enabled")):
        return False
    start_s = settings.get("quiet_hours_start")
    end_s = settings.get("quiet_hours_end")
    if not isinstance(start_s, str) or not isinstance(end_s, str):
        return False
    start_m = _parse_hhmm_to_minutes(start_s)
    end_m = _parse_hhmm_to_minutes(end_s)
    if start_m is None or end_m is None:
        return False
    if start_m == end_m:
        return False
    lm = _local_minutes_from_utc(now_utc, str(settings.get("timezone") or "") or None)
    if start_m < end_m:
        return start_m <= lm < end_m
    return lm >= start_m or lm < end_m


def should_skip_in_app_notification_v1(
    settings: dict[str, Any],
    *,
    now_utc: datetime,
    resolved_priority: str,
    channel: str,
) -> bool:
    """
    Return True if an in-app CRM bell row should not be created.

    - ``channels.in_app`` false → skip all in-app inserts for this user.
    - Quiet hours: skip ``normal`` and ``high``; always allow ``critical``.
    """
    ch = str(channel or "in_app").strip().lower() or "in_app"
    if ch != "in_app":
        return False
    channels = settings.get("channels")
    if isinstance(channels, dict) and channels.get("in_app") is False:
        return True
    pri = str(resolved_priority or "").strip().lower()
    if pri == "critical":
        return False
    if is_within_quiet_hours_v1(settings, now_utc=now_utc):
        return pri in {"normal", "high"}
    return False


__all__ = [
    "is_within_quiet_hours_v1",
    "normalize_notification_settings_v1",
    "should_skip_in_app_notification_v1",
]
